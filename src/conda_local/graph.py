import logging
from typing import Final, Iterable, Iterator, TypeVar, Union, overload

import networkx as nx

from conda_local.external import (
    MatchSpec,
    PackageRecord,
    create_spec_lookup,
    query_channel,
)
from conda_local.grouping import Grouping
from conda_local.stream import UniqueAppendableStream

_LOGGER = logging.getLogger(__name__)

_DependencyNode = Union[str, PackageRecord]
_T = TypeVar("_T")


class DependencyGraph:
    """A `networkx.DiGraph` wrapper for the directed anaconda dependency graph.

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


def construct_dependency_graph(
    channel: str, subdirs: Iterable[str], specs: Iterable[str]
) -> DependencyGraph:
    """Constructs a dependency graph from match specifications over an anaconda channel.

    Args:
        channel: The canonical name, URL, or URI of an anaconda channel.
        subdirs: The platforms sub-directories o include in the dependency graph.
        specs: The anaconda match specifications used in the dependency graph.

    Returns:
        DependencyGraph: _description_
    """

    graph = DependencyGraph(specs)
    constraints = create_spec_lookup(specs)
    spec_stream = UniqueAppendableStream(specs)

    for spec in spec_stream:
        _LOGGER.info("Processing spec: %s", spec)
        graph.add_spec(spec)

        for record in query_channel(channel, subdirs, spec):
            if _is_record_constrainted(record, constraints):
                _LOGGER.debug("Ignoring constrained record: %s", record)
                continue

            _LOGGER.debug("Processing record: %s", record)
            graph.add_candidate(spec, record)

            for dependency in record.depends:
                _LOGGER.debug(
                    "Processing record dependency: %s -- %s", record, dependency
                )
                spec_stream.append(dependency)
                graph.add_dependency(record, dependency)

    # Exclude unsatisfied / orphaned nodes
    for spec in graph.unsatisfied_specs():
        _exclude_unsatisfied_nodes(graph, spec)

    return graph


def _exclude_orphaned_nodes(graph: DependencyGraph, spec: str) -> None:
    """Recursively excludes nodes from a dependency graph if they are orphaned.

    A match specification node is considered to be orphaned if it is a non-root node
    that has no valid parent nodes.

    Args:
        graph: An initialized dependency graph object.
        spec: A match specification node within the dependency graph.
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
            _LOGGER.debug("Excluding candidate of orphaned spec: %s -> %s", child, spec)
            graph.mark_exclude(child)
            for grandchildren in graph.successors(child):
                _exclude_orphaned_nodes(graph, grandchildren)


def _exclude_unsatisfied_nodes(graph: DependencyGraph, spec: str) -> None:
    """Recursively excludes nodes from a dependency graph if they are unsatisfied.

    A match specification node is considered to be unsatisfied if it has no valid child
    nodes.

    Args:
        graph: An initialized dependency graph object.
        spec: A match specification node within the dependency graph.
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
            _exclude_orphaned_nodes(graph, sibling)

        # Excluded parent records may create unsatisfied grandparent specs
        for grandparent in graph.predecessors(parent):
            _exclude_unsatisfied_nodes(graph, grandparent)


def _is_record_constrainted(
    record: PackageRecord, constraints: Grouping[str, MatchSpec]
) -> bool:
    """Determines if a package record is constrained.

    A package record is considered to be constrained if it does not match any of the
    constraints within a group corresponding to the package name. If there are no
    corresponding groups for the current package record then it is considered
    unconstrained.

    Args:
        record: The package record that will be tested against constraints.
        constraints: Match specifications grouped by package name.

    Returns:
        True if a package is constrainted, False otherwise.
    """
    if record.name in constraints.keys():
        return not all(const.match(record) for const in constraints[record.name])
    return False
