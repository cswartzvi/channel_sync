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

LOGGER = logging.Logger(__name__)

_DependencyNode = Union[str, PackageRecord]
_T = TypeVar("_T")


class DependencyFinder:
    """Anaconda package dependency finder.

    Note: This is not a package solver that attempts to find a singular path
    through a dependency graph. Instead, the purpose of this class is to
    recursively find *all* package records, within a channel, that satisfy
    the dependencies of a given package. In terms of the dependency graph
    this is equivalent to finding all the successor nodes of a dependency
    that are themselves satisfied by at least one package.

    Args:
        channel: The canonical name, URL, or URI of an anaconda channel.
        platforms: The platforms to include in the solution. Note: Does not
            automatically include the "noarch" platform.
    """

    def __init__(self, channel: str, subdirs: Iterable[str]) -> None:
        self._channel = channel
        self._subdirs = list(subdirs)

    def search(
        self, specs: Iterable[str]
    ) -> Tuple[Iterator[PackageRecord], nx.DiGraph]:
        """Searches for package dependencies for given anaconda match specifications.

        Args:
            specs: The anaconda match specifications used in the dependency search.

        Returns:
            A tuple of a package record iterator and the annotated dependency graph.
        """
        constraints = create_spec_lookup(specs)
        graph = self._construct_dependency_graph(specs, constraints)
        records = self._extract_records(graph)
        return records, graph

    def _construct_dependency_graph(
        self, specs: Iterable[str], constraints: Grouping[str, MatchSpec]
    ) -> "_DependencyGraph":
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
        graph = _DependencyGraph()
        spec_stream = _UpdateStream(specs)

        for spec in spec_stream:
            LOGGER.info("Processing spec: %s", spec)
            graph.add_spec(spec)
            for record in query_channel(self._channel, [spec], self._subdirs):
                if self._is_constrainted(record, constraints):
                    LOGGER.debug("Constrained record: %s", record)
                    continue
                LOGGER.debug("Processing record: %s", record)
                graph.add_candidate(spec, record)

                for dependency in record.depends:
                    spec_stream.add(dependency)
                    graph.add_dependency(record, dependency)

        for spec in graph.unsatisfied_specs():
            self._exclude_unsatisfied_nodes(spec, graph)

        return graph

    def _exclude_unsatisfied_nodes(self, spec: str, graph: "_DependencyGraph") -> None:
        """Excludes (marks include = False) unsatisfied nodes in a dependency graph.

        Args:
            spec: Starting match specification node in the dependency graph.
            graph: A dependency graph consisting of match specifications
                and package records.
        """
        # A spec is considered satisfied if it has at least one child record
        if any(True for _ in graph.successors(spec)):
            return  # spec is satisfied

        graph.mark_exclude(spec)  # spec is unsatisfied

        for parent in graph.predecessors(spec):
            # All parent records of an unsatisfied specs are excluded
            graph.mark_exclude(parent)

            # Excluded parent records may create orphaned sibling specs
            for sibling in graph.successors(parent):
                self._exclude_orphaned_nodes(sibling, graph)

            # Excluded parent records may create unsatisfied grandparent specs
            for grandparent in graph.predecessors(parent):
                self._exclude_unsatisfied_nodes(grandparent, graph)

    def _extract_records(self, graph: "_DependencyGraph") -> Iterator[PackageRecord]:
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

    def _exclude_orphaned_nodes(self, spec: str, graph: "_DependencyGraph") -> None:
        """Excludes (marks include = False) orphaned nodes in a dependency graph.

        Args:
            spec: Starting match specification node in the dependency graph.
            graph: A dependency graph consisting of match specifications
                and package records.
        """
        # A spec is not considered orphaned if it has parent records
        if any(True for _ in graph.predecessors(spec)):
            return  # spec is not orphaned

        graph.mark_exclude(spec)

        # Child records are considered orphaned if they have no other parent specs
        for child in graph.successors(spec):
            if all(False for _ in graph.predecessors(child)):
                graph.mark_exclude(child)
                for grandchildren in graph.successors(child):
                    self._exclude_orphaned_nodes(grandchildren, graph)


class _DependencyGraph:
    """A ``networkx.DiGraph`` wrapper for dealing with str / PackageRecords nodes."""

    _attribute: Final[str] = "include"

    def __init__(self) -> None:
        self._graph = nx.DiGraph()

    @property
    def specs(self) -> Iterator[str]:
        for node in self._graph.nodes:
            if isinstance(node, str) and self.is_included(node):
                yield node

    @property
    def records(self) -> Iterator[PackageRecord]:
        for node in self._graph.nodes:
            if isinstance(node, PackageRecord) and self.is_included(node):
                yield node

    def add_spec(self, spec: str) -> None:
        if spec not in self._graph.nodes:
            self._graph.add_node(spec, **{self._attribute: True})

    def _add_record(self, record: PackageRecord) -> None:
        self._graph.add_node(record, **{self._attribute: True})

    def add_candidate(self, spec: str, candidate: PackageRecord) -> None:
        self.add_spec(spec)
        self._add_record(candidate)
        self._graph.add_edge(spec, candidate)

    def add_dependency(self, record: PackageRecord, dependency: str) -> None:
        self._add_record(record)
        self.add_spec(dependency)
        self._graph.add_edge(record, dependency)

    def is_included(self, node: _DependencyNode) -> bool:
        return self._graph.nodes[node][self._attribute]

    def mark_exclude(self, node: _DependencyNode):
        self._graph.nodes[node][self._attribute] = False

    @overload
    def predecessors(self, node: str) -> Iterator[PackageRecord]:
        ...

    @overload
    def predecessors(self, node: PackageRecord) -> Iterator[str]:
        ...

    def predecessors(
        self, node: _DependencyNode
    ) -> Union[Iterator[str], Iterator[PackageRecord]]:
        for pred in self._graph.predecessors(node):
            if self.is_included(pred):
                yield pred

    @overload
    def successors(self, node: str) -> Iterator[PackageRecord]:
        ...

    @overload
    def successors(self, node: PackageRecord) -> Iterator[str]:
        ...

    def successors(
        self, node: Union[str, PackageRecord]
    ) -> Union[Iterator[str], Iterator[PackageRecord]]:
        for suc in self._graph.successors(node):
            if self.is_included(suc):
                yield suc

    def unsatisfied_specs(self) -> Iterator[str]:
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
