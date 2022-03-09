import logging
from typing import Final, Iterable, Iterator, Tuple, Union, overload

import networkx as nx

from conda_local.external import (
    MatchSpec,
    PackageRecord,
    create_spec_lookup,
    query_channels,
)
from conda_local.utils import Grouping, UniqueStream

LOGGER = logging.Logger(__name__)


DependencyNode = Union[str, PackageRecord]


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

    def __init__(self, channels: Iterable[str], subdirs: Iterable[str]) -> None:
        self._channels = list(channels)
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
        spec_stream = UniqueStream(specs)

        for spec in spec_stream:
            LOGGER.info("Processing spec: %s", spec)
            graph.add_spec(spec)
            for record in query_channels(self._channels, self._subdirs, [spec]):
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
        if not graph.is_included(spec):
            return  # already excluded

        # A spec is considered satisfied if at least one child record is marked
        # as included.
        if any(graph.is_included(child) for child in graph.successors(spec)):
            return  # satisfied by a child, stop search

        graph.mark_exclude(spec)

        # All parent records of an unsatisfied specs are excluded
        for parent in graph.predecessors(spec):
            graph.mark_exclude(parent)

            # Excluded parent records may create orphaned sibling specs
            for sibling in graph.successors(parent):
                if sibling != spec:
                    self._exclude_orphaned_nodes(sibling, graph)

            # Excluded records may create unsatisfied grandparent spec
            for grandparent in graph.predecessors(parent):
                self._exclude_unsatisfied_nodes(grandparent, graph)

    def _extract_records(self, graph: "_DependencyGraph") -> Iterator[PackageRecord]:
        """Yields included package records from the dependency graph.

        Args:
            graph: A dependency graph consisting of match specifications
                and package records.
        """
        for record in graph.records:
            if graph.is_included(record):
                yield record

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
        if not graph.is_included(spec):
            return  # already excluded

        # A spec is orphaned if no parent records are included.
        for parent in graph.predecessors(spec):
            if graph.is_included(parent):
                return  # not orphaned, stop search

        graph.mark_exclude(spec)

        # A spec successor child is only considered orphaned if
        # it is not a successor of another spec.
        for children in graph.successors(spec):
            if not graph.is_included(children):
                continue

            orphaned_children = True
            for sibling in graph.predecessors(children):
                if sibling == spec:
                    continue  # skip self
                if graph.is_included(sibling):
                    orphaned_children = False
                    break

            if orphaned_children:
                graph.mark_exclude(children)
                for grandchildren in graph.successors(children):
                    self._exclude_orphaned_nodes(grandchildren, graph)


class _DependencyGraph:

    _attribute: Final[str] = "include"

    def __init__(self) -> None:
        self._graph = nx.DiGraph()

    @property
    def specs(self) -> Iterator[str]:
        yield from (node for node in self._graph.nodes if isinstance(node, str))

    @property
    def records(self) -> Iterator[PackageRecord]:
        yield from (
            node for node in self._graph.nodes if isinstance(node, PackageRecord)
        )

    def add_spec(self, spec: str) -> None:
        if spec not in self._graph.nodes:
            self._graph.add_node(spec, **{self._attribute: True})

    def _add_record(self, record: PackageRecord) -> None:
        self._graph.add_node(record, **{self._attribute: True})

    def add_candidate(self, spec: str, record: PackageRecord) -> None:
        self.add_spec(spec)
        self._add_record(record)
        self._graph.add_edge(spec, record)

    def add_dependency(self, record: PackageRecord, spec: str) -> None:
        self._add_record(record)
        self.add_spec(spec)
        self._graph.add_edge(record, spec)

    def is_included(self, node: DependencyNode) -> bool:
        return self._graph.nodes[node][self._attribute]

    def mark_exclude(self, node: DependencyNode):
        self._graph.nodes[node][self._attribute] = False

    @overload
    def predecessors(self, node: str) -> Iterator[PackageRecord]:
        ...

    @overload
    def predecessors(self, node: PackageRecord) -> Iterator[str]:
        ...

    def predecessors(
        self, node: DependencyNode
    ) -> Union[Iterator[str], Iterator[PackageRecord]]:
        yield from self._graph.predecessors(node)

    @overload
    def successors(self, node: str) -> Iterator[PackageRecord]:
        ...

    @overload
    def successors(self, node: PackageRecord) -> Iterator[str]:
        ...

    def successors(
        self, node: Union[str, PackageRecord]
    ) -> Union[Iterator[str], Iterator[PackageRecord]]:
        yield from self._graph.successors(node)

    def unsatisfied_specs(self) -> Iterator[str]:
        yield from (spec for spec in self.specs if self._graph.out_degree(spec) == 0)
