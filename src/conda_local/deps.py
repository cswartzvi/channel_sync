import logging
from typing import Final, Iterable, Iterator, Tuple, TypeVar, Union, overload

import networkx as nx

from conda_local.external import (
    MatchSpec,
    PackageRecord,
    create_spec_lookup,
    query_channel,
)
from conda_local.grouping import Grouping

_LOGGER = logging.getLogger(__name__)

_DependencyNode = Union[str, PackageRecord]
_T = TypeVar("_T")


class DependencyFinder:
    """Anaconda package dependency finder.

    This solver does **not** attempt to find a singular path through a dependency graph
    (like the solver within the main `conda` executable). Instead, this solver
    recursively finds all package records that

    Args:
        channel: The canonical name, URL, or URI of an anaconda channel.
        platforms: The platforms to include in the solution. Note: Does not
            automatically include the "noarch" platform.
    """

    def __init__(self, channel: str, subdirs: Iterable[str]) -> None:
        self._channel = channel
        self._subdirs = list(subdirs)

    def search(
        self, specs: Iterable[str], latest: bool = False
    ) -> Tuple[Iterator[PackageRecord], nx.DiGraph]:
        """S

        Args:
            specs: The anaconda match specifications used in the dependency search.

        Returns:
            A tuple of a package record iterator and the annotated dependency graph.
        """
        constraints = create_spec_lookup(specs)
        graph = self._construct_dependency_graph(specs, constraints, latest)
        records = self._extract_records(graph)
        return records, graph

    def _construct_dependency_graph(
        self, specs: Iterable[str], constraints: Grouping[str, MatchSpec], latest: bool,
    ) -> "DependencyGraph":
        """Constrcuts a dependency graph for the current calculation.

        Args:
            specs: An iterable of match specifications used to construct the graph.
            constraints: The match specifications for package constraints grouped
                by package name.

        Returns:
            A directed graph of recursively alternating match specification objects
            (root node) and package record objects. Additionally, each node has an
            attribute "include" that indicates whether or not a node is included in
            the final solution.
        """
        graph = DependencyGraph(specs)
        spec_stream = _UpdateStream(specs)

        for spec in spec_stream:
            _LOGGER.info("Processing spec: %s", spec)
            graph.add_spec(spec)
            for record in query_channel(self._channel, [spec], self._subdirs):
                if self._is_constrainted(record, constraints):
                    _LOGGER.debug("Ignoring constrained record: %s", record)
                    continue

                _LOGGER.debug("Processing record: %s", record)
                graph.add_candidate(spec, record)

                for dependency in record.depends:
                    _LOGGER.debug(
                        "Processing record dependency: %s -- %s", record, dependency
                    )
                    spec_stream.add(dependency)
                    graph.add_dependency(record, dependency)

        for spec in graph.unsatisfied_specs():
            self._exclude_unsatisfied_nodes(spec, graph)

        return graph

    def _exclude_unsatisfied_nodes(self, spec: str, graph: "DependencyGraph") -> None:
        """Excludes nodes in the dependency graph that are determined to be unsatisfied.

        Args:
            spec: Starting match specification node in the dependency graph.
            graph: A dependency graph consisting of match specifications
                and package records.
        """
        # A spec is considered satisfied if it has at least one child record
        if any(True for _ in graph.successors(spec)):
            return  # spec is satisfied

        if graph.is_root(spec):
            _LOGGER.debug("Excluding unsatisfied ROOT spec: %s", spec)
        else:
            _LOGGER.debug("Excluding unsatisfied spec: %s", spec)
        graph.mark_exclude(spec)  # spec is unsatisfied

        for parent in graph.predecessors(spec):
            # All parent records of an unsatisfied specs are excluded
            _LOGGER.debug(
                "Excluding record with unsatisfied dependency: %s -> %s", parent, spec
            )
            graph.mark_exclude(parent)

            # Excluded parent records may create orphaned sibling specs
            for sibling in graph.successors(parent):
                self._exclude_orphaned_nodes(sibling, graph)

            # Excluded parent records may create unsatisfied grandparent specs
            for grandparent in graph.predecessors(parent):
                self._exclude_unsatisfied_nodes(grandparent, graph)

    def _extract_records(self, graph: "DependencyGraph") -> Iterator[PackageRecord]:
        """Yields included package records from the dependency graph.

        Args:
            graph: A dependency graph consisting of match specifications
                and package records.
        """
        yield from graph.records

    def _is_constrainted(
        self, record: PackageRecord, constraints: Grouping[str, MatchSpec]
    ) -> bool:
        """Determines if a package record is constrained.

        Args:
            record: The package record that will be tested against constraints.
            constraints: The match specifications for package constraints grouped
                by package name.

        Returns:
            True if a package is constrainted (does not match a constraint) or
            False otherwise (matches a constraint, or of a package type that is not
            constrained).
        """
        if record.name in constraints.keys():
            return not all(const.match(record) for const in constraints[record.name])
        return False

    def _exclude_orphaned_nodes(self, spec: str, graph: "DependencyGraph") -> None:
        """Excludes nodes in the dependency graph that are determined to be orphaned.

        Args:
            spec: Starting match specification node in the dependency graph.
            graph: A dependency graph consisting of match specifications
                and package records.
        """
        # Root nodes cannot be considered orphaned
        if graph.is_root(spec):
            return

        # A spec is not considered orphaned if it has parent records
        if any(True for _ in graph.predecessors(spec)):  # True if any predecessors
            return  # spec is not orphaned

        _LOGGER.debug("Excluding orphaned spec: %s", spec)
        graph.mark_exclude(spec)

        # Child records are considered orphaned if they have no other parent specs
        for child in graph.successors(spec):
            if all(False for _ in graph.predecessors(child)):  # True if no predecessors
                _LOGGER.debug(
                    "Excluding candidate of orphaned spec: %s -> %s", child, spec
                )
                graph.mark_exclude(child)
                for grandchildren in graph.successors(child):
                    self._exclude_orphaned_nodes(grandchildren, graph)


class DependencyGraph:
    """A `networkx.DiGraph` wrapper for the anaconda dependency directed graph.

    The dependency graph contains alternating match specification strings and package
    record nodes starting with match specification strings at the roots. Both types of
    nodes are initially *included* but can be marked as *excluded* via interactions
    with this class.

    Args:
        spec_root: Root match specification strings.
    """

    _attribute: Final[str] = "include"
    _root: Final[str] = "root"

    def __init__(self, spec_roots: Iterable[str]) -> None:
        self._graph = nx.DiGraph()
        for spec_root in spec_roots:
            self._add_spec_root(spec_root)

    @property
    def specs(self) -> Iterator[str]:
        """Returns all currently included match specification strings."""
        for node in self._graph.nodes:
            if isinstance(node, str) and self.is_included(node):
                yield node

    @property
    def records(self) -> Iterator[PackageRecord]:
        """Returns all currently included package records objects."""
        for node in self._graph.nodes:
            if isinstance(node, PackageRecord) and self.is_included(node):
                yield node

    def add_spec(self, spec: str) -> None:
        """Adds a non-root match specification string to the graph."""
        if spec not in self._graph.nodes:
            self._graph.add_node(spec, **{self._attribute: True, self._root: False})

    def _add_spec_root(self, spec: str) -> None:
        """Adds a root match specification string to the graph."""
        self._graph.add_node(spec, **{self._attribute: True, self._root: True})

    def _add_record(self, record: PackageRecord) -> None:
        """Adds a package record object to the graph."""
        self._graph.add_node(record, **{self._attribute: True})

    def add_candidate(self, spec: str, candidate: PackageRecord) -> None:
        """Connects a match specification string to a package records candidate.

        Candidates are package records that *may* satisfy a match specification. Nodes
        that do not currently exists in the underlying graph are added.
        """
        self.add_spec(spec)
        self._add_record(candidate)
        self._graph.add_edge(spec, candidate)

    def add_dependency(self, record: PackageRecord, dependency: str) -> None:
        """Connects a package record to a match specification dependency.

        Dependencies are match specification strings that are required to be installed
        by a package record. Nodes that do not currently exists in the underlying graph
        are added.
        """
        self._add_record(record)
        self.add_spec(dependency)
        self._graph.add_edge(record, dependency)

    def is_included(self, node: _DependencyNode) -> bool:
        """Returns True if the specified node is marked include, False otherwise."""
        return self._graph.nodes[node][self._attribute]

    def is_root(self, node: _DependencyNode) -> bool:
        """Returns True if the specified node is a root node, False otherwise."""
        return self._graph.nodes[node][self._root]

    def mark_exclude(self, node: _DependencyNode) -> None:
        """Marks a specified node as excluded."""
        self._graph.nodes[node][self._attribute] = False

    @overload
    def predecessors(self, node: str) -> Iterator[PackageRecord]:
        """Returns package record predecessors of a match specifcation node."""
        ...

    @overload
    def predecessors(self, node: PackageRecord) -> Iterator[str]:
        """Returns match specifcation predecessors of a package records node."""
        ...

    def predecessors(
        self, node: _DependencyNode
    ) -> Union[Iterator[str], Iterator[PackageRecord]]:
        """Returns a predecessor (parents) nodes for the specified node."""
        for pred in self._graph.predecessors(node):
            if self.is_included(pred):
                yield pred

    @overload
    def successors(self, node: str) -> Iterator[PackageRecord]:
        """Returns package record successors of a match specifcation node."""
        ...

    @overload
    def successors(self, node: PackageRecord) -> Iterator[str]:
        """Returns match specifcation successors of a package records node."""
        ...

    def successors(
        self, node: Union[str, PackageRecord]
    ) -> Union[Iterator[str], Iterator[PackageRecord]]:
        """Returns a successor (children) nodes for the specified node."""
        for suc in self._graph.successors(node):
            if self.is_included(suc):
                yield suc

    def unsatisfied_specs(self) -> Iterator[str]:
        """Yields all unsatisfied match specification nodes.

        Unsatisfied match specification nodes have no included package records
        candidates.
        """
        yield from (spec for spec in self.specs if self._graph.out_degree(spec) == 0)


class _UpdateStream(Iterator[_T]):
    """A stream of unique items that is appendable during iteration.

    Args:
        items: Initial items in the stream.
    """

    def __init__(self, items: Iterable[_T]):
        self._data = list(items)

    def add(self, item: _T) -> None:
        if item in self._data:
            return  # already exists
        self._data.append(item)

    def __iter__(self) -> Iterator[_T]:
        self._index = 0
        return self

    def __next__(self) -> _T:
        try:
            item = self._data[self._index]
            self._index += 1
        except IndexError:
            raise StopIteration
        return item
