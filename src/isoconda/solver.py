from typing import Iterable, Iterator, Set, Tuple, Union

import networkx as nx

from isoconda.grouping import Grouping, group_by
from isoconda.stream import UniqueStream
from isoconda.wrapper import ChannelData, PackageRecord


class PackageSolver:
    """Anaconda package record solver.

    Args:
        channel: The canonical name, URL, or URI of the anaconda channel.
        platforms: The platforms to include in the solution. Does not
            automatically include the noarch platform.
    """

    _INCLUDE = "include"

    def __init__(self, channel: str, platforms: Union[str, Iterable[str]]) -> None:
        self._channel_data = ChannelData(channel, platforms)

    def solve(self, specs: Iterable[str]) -> Tuple[Set[PackageRecord], nx.DiGraph]:
        constraints = group_by(self._channel_data.query(specs), lambda pkg: pkg.name)
        graph = self._construct_dependency_graph(specs, constraints)
        records = set(self._extract_records(graph))
        return records, graph

    def _construct_dependency_graph(
        self, specs: Iterable[str], constraints: Grouping[str, PackageRecord]
    ) -> nx.DiGraph:
        """Constrcuts a dependency graph for the current calculation.

        Args:
            specs: An iterable of match specifications used to construct the graph.
            constraints: Package records, grouped by package name, that constrain
                the construction of the dependency graph.

        Returns:
            A directed graph of recursively alternating match specification strings
            (root node) and package record objects. Additionally, each node has an
            attribute "include" that indicates whether or not a node is included in
            the final solution.
        """
        graph = nx.DiGraph()
        spec_stream = UniqueStream(specs)

        for spec in spec_stream:
            graph.add_node(spec, **{self._INCLUDE: True})
            for record in self._channel_data.query(spec):
                if self._is_constrainted(record, constraints):
                    continue
                graph.add_node(record, **{self._INCLUDE: True})
                graph.add_edge(spec, record)

                for depends_spec in record.depends:
                    spec_stream.add(depends_spec)
                    graph.add_node(depends_spec, **{self._INCLUDE: True})
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
        if not graph.nodes[spec][self._INCLUDE]:
            return  # already excluded

        # A spec is considered unsatisfied if all of it's successors
        # (children) are excluded.
        successors = list(graph.successors(spec))
        if successors:
            for children in successors:
                if graph.nodes[children][self._INCLUDE]:
                    return
        graph.nodes[spec][self._INCLUDE] = False

        # All dependent (parent) records of an unsatisfied spec are excluded
        for parent in graph.predecessors(spec):
            graph.nodes[parent][self._INCLUDE] = False

            # Excluded records may create orphaned (sibling) specs
            for sibling in graph.successors(parent):
                if sibling != spec:
                    self._exclude_orphaned_nodes(sibling, graph)

            # Excluded records may create unsatisfied (grandparent) spec
            for grandparent in graph.predecessors(parent):
                self._exclude_unsatisfied_nodes(grandparent, graph)

    def _extract_records(self, graph: nx.DiGraph) -> Iterator[PackageRecord]:
        """Yields included package records from the dependency graph.

        Args:
            graph: A dependency graph consisting of match specifications
                and package records.
        """
        for node in graph.nodes:
            if isinstance(node, PackageRecord) and graph.nodes[node][self._INCLUDE]:
                yield node

    def _is_constrainted(
        self, record: PackageRecord, constraints: Grouping[str, PackageRecord]
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
            if record not in constraints[record.name]:
                return True
        return False

    def _exclude_orphaned_nodes(self, spec: str, graph: nx.DiGraph) -> None:
        """Excludes (marks include = False) orphaned nodes in a dependency graph.

        Args:
            spec: Starting match specification node in the dependency graph.
            graph: A dependency graph consisting of match specifications
                and package records.
        """
        if not graph.nodes[spec][self._INCLUDE]:
            return  # already excluded

        # A spec is only orphaned if none of it's predecessor (parent)
        # package record are included.
        for parent in graph.predecessors(spec):
            if graph.nodes[parent][self._INCLUDE]:
                return  # not orphaned, dependency for another package
        graph.nodes[spec][self._INCLUDE] = False

        # A spec successor (child) is only considered orphaned if
        # it is not a successor of another spec.
        for children in graph.successors(spec):
            if not graph.nodes[children][self._INCLUDE]:
                continue

            orphaned_children = True
            for sibling in graph.predecessors(children):
                if sibling == spec:
                    continue  # skip self
                if graph.nodes[sibling][self._INCLUDE]:
                    orphaned_children = False
                    break

            if orphaned_children:
                graph.nodes[children][self._INCLUDE] = False
                for grandchildren in graph.successors(children):
                    self._exclude_orphaned_nodes(grandchildren, graph)

    def reload(self):
        """Reloads the associated channel."""
        self._channel_data.reload()
