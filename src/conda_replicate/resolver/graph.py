import logging
from typing import Any, Iterable, Iterator, Set

import networkx as nx

from conda_replicate import CondaReplicateException
from conda_replicate.adapters.package import CondaPackage
from conda_replicate.resolver.query import PackageQuery

logger = logging.getLogger(__name__)


def create_dependency_graph(specs: Iterable[str], query: PackageQuery) -> nx.DiGraph:
    """Returns the main resolution graph and root nodes from given parameters.

    The resolution graph is a directed graph made of alternating levels of match
    specifications strings and conda package objects. The graph has multiple roots
    which are associated with the required match specification parameters. Starting
    from the roots, packages and their dependencies are recursively added to the
    graph unless a package is determined to be constrained via the parameters.
    """

    graph = nx.DiGraph()
    _populate_graph(graph, specs, query)
    logger.info("Initial graph G(V%d, E=%d)", len(graph.nodes), len(graph.edges))
    _prune_unsatisfied_nodes(graph)
    _prune_disconnected_nodes(graph, specs)
    _verify_graph_requirements(graph, specs)
    logger.info("Final graph G(V=%d, E=%d)", len(graph.nodes), len(graph.edges))
    return graph


def extract_dependency_graph_packages(graph: nx.DiGraph) -> Iterator[CondaPackage]:
    for node in graph.nodes:
        if isinstance(node, CondaPackage):
            yield node


def _populate_graph(
    graph: nx.DiGraph, specs: Iterable[str], query: PackageQuery
) -> None:
    """Populate the dependency graph"""
    specs_to_process: Set[str] = set()
    specs_processed: Set[str] = set()

    for spec in specs:
        logger.info("Adding root node: %s", spec)
        specs_to_process.add(spec)
        graph.add_node(spec, root=True)

    while specs_to_process:
        spec = specs_to_process.pop()
        specs_processed.add(spec)
        logger.info("Processing spec %s", spec)

        for package in query(spec):

            if package not in graph:
                graph.add_node(package)

            logger.info("Connecting spec %s to package %s", spec, package)
            graph.add_edge(spec, package)

            for depend in package.depends:
                if depend not in graph:
                    graph.add_node(depend)

                logger.info("Connecting package %s to spec %s", package, depend)
                graph.add_edge(package, depend)

                if depend not in specs_processed:
                    specs_to_process.add(depend)
    return graph


def _prune_unsatisfied_nodes(graph: nx.DiGraph) -> None:
    """Prune unsatisfied specification nodes from a dependency graph.

    A specification node is considered unsatisfied if it has no successors.
    """

    def prune_unsatisfied(node: Any) -> None:

        if not isinstance(node, str):
            return
        if node not in graph:
            return
        if list(graph.successors(node)):
            return

        logger.info("Removing unsatisfied spec: %s", node)
        parents = list(graph.predecessors(node))
        graph.remove_node(node)

        for parent in parents:
            if parent not in graph:
                continue

            logger.info("Removing package with missing dependency: %s", parent)
            grandparents = list(graph.predecessors(parent))
            graph.remove_node(parent)

            for grandparent in grandparents:
                prune_unsatisfied(grandparent)

    logger.info("Pruning unsatisfied nodes")
    for node in set(graph):
        prune_unsatisfied(node)


def _prune_disconnected_nodes(graph: nx.DiGraph, specs: Iterable[str]) -> None:
    """Prune disconnected nodes - nodes without a path to at least one root node."""

    connected = set()
    for spec in specs:
        if spec not in graph.nodes:
            continue
        connected.update(nx.dfs_preorder_nodes(graph, spec))

    disconnected = set(graph.nodes) - connected
    for node in disconnected:
        logger.info("Pruning disconnected node: %s", node)
        graph.remove_node(node)


def _verify_graph_requirements(graph: nx.DiGraph, specs: Iterable[str]) -> None:
    missing = set(spec for spec in specs if spec not in graph)
    if missing:
        raise UnsatisfiedRequirementsError(missing)


class UnsatisfiedRequirementsError(CondaReplicateException):
    """Exception raised when required specifications could not be satisfied."""

    def __init__(self, missing: Iterable[str]) -> None:
        self.missing = sorted(missing)
        message = f"Missing required packages: {missing!r}"
        super().__init__(message)
