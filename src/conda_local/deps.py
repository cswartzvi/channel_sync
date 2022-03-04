import logging
from typing import Iterable, Iterator, Tuple

import networkx as nx

from conda_local.external import (
    MatchSpec,
    PackageRecord,
    create_spec_lookup,
    query_channels,
)
from conda_local.utils import Grouping, UniqueStream

LOGGER = logging.Logger(__name__)


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

    _tag = "include"

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
    ) -> nx.DiGraph:
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
        graph = nx.DiGraph()
        spec_stream = UniqueStream(specs)

        for spec in spec_stream:
            LOGGER.info("Processing spec: %s", spec)
            graph.add_node(spec, **{self._tag: True})
            for record in query_channels(self._channels, self._subdirs, [spec]):
                if self._is_constrainted(record, constraints):
                    continue
                LOGGER.debug("Processing spec: %s", spec)
                graph.add_node(record, **{self._tag: True})
                graph.add_edge(spec, record)

                for depends_spec in record.depends:
                    spec_stream.add(depends_spec)
                    graph.add_node(depends_spec, **{self._tag: True})
                    graph.add_edge(record, depends_spec)

        for node in graph.nodes:
            if isinstance(node, str) and graph.out_degree(node) == 0:
                self._exclude_unsatisfied_nodes(node, graph)

        return graph

    def _exclude_unsatisfied_nodes(self, spec: str, graph: nx.DiGraph) -> None:
        """Excludes (marks include = False) unsatisfied nodes in a dependency graph.

        Args:
            spec: Starting match specification node in the dependency graph.
            graph: A dependency graph consisting of match specifications
                and package records.
        """
        if not graph.nodes[spec][self._tag]:
            return  # already excluded

        # A spec is considered satisfied if at least one child is included.
        children = list(graph.successors(spec))
        if children:
            for child in children:
                if graph.nodes[child][self._tag]:
                    return  # satisfied by a child, stop search

        graph.nodes[spec][self._tag] = False

        # All parent records of an unsatisfied spec are excluded
        for parent in graph.predecessors(spec):
            graph.nodes[parent][self._tag] = False

            # Excluded records may create orphaned sibling specs
            for sibling in graph.successors(parent):
                if sibling != spec:
                    self._exclude_orphaned_nodes(sibling, graph)

            # Excluded records may create unsatisfied grandparent spec
            for grandparent in graph.predecessors(parent):
                self._exclude_unsatisfied_nodes(grandparent, graph)

    def _extract_records(self, graph: nx.DiGraph) -> Iterator[PackageRecord]:
        """Yields included package records from the dependency graph.

        Args:
            graph: A dependency graph consisting of match specifications
                and package records.
        """
        for node in graph.nodes:
            if isinstance(node, PackageRecord) and graph.nodes[node][self._tag]:
                yield node

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

    def _exclude_orphaned_nodes(self, spec: str, graph: nx.DiGraph) -> None:
        """Excludes (marks include = False) orphaned nodes in a dependency graph.

        Args:
            spec: Starting match specification node in the dependency graph.
            graph: A dependency graph consisting of match specifications
                and package records.
        """
        if not graph.nodes[spec][self._tag]:
            return  # already excluded

        # A spec is orphaned if none of it's parent records are included.
        for parent in graph.predecessors(spec):
            if graph.nodes[parent][self._tag]:
                return  # not orphaned, stop search

        graph.nodes[spec][self._tag] = False

        # A spec successor child is only considered orphaned if
        # it is not a successor of another spec.
        for children in graph.successors(spec):
            if not graph.nodes[children][self._tag]:
                continue

            orphaned_children = True
            for sibling in graph.predecessors(children):
                if sibling == spec:
                    continue  # skip self
                if graph.nodes[sibling][self._tag]:
                    orphaned_children = False
                    break

            if orphaned_children:
                graph.nodes[children][self._tag] = False
                for grandchildren in graph.successors(children):
                    self._exclude_orphaned_nodes(grandchildren, graph)
