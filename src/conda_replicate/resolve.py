from __future__ import annotations

import logging
from typing import Any, Iterable, Iterator, Set, Tuple

import networkx as nx

from conda_replicate import CondaReplicateException
from conda_replicate.adapters.channel import CondaChannel
from conda_replicate.adapters.package import CondaPackage
from conda_replicate.adapters.specification import CondaSpecification
from conda_replicate.group import groupby

log = logging.getLogger(__name__)


class Resolver:
    """Channel based package and dependency resolution."""

    _root_attribute = "root"

    def __init__(self, source: CondaChannel, strict: bool = False) -> None:
        self.source = source
        self.strict = strict

    def resolve(self, parameters: Parameters) -> Tuple[CondaPackage, ...]:
        """Execute the resolution algorithm using specified parameters."""

        graph, roots = self._construct_graph(parameters)

        log.debug("Initial graph G(V%d, E=%d)", len(graph.nodes), len(graph.edges))

        self._prune_unsatisfied_nodes(graph)
        self._verify_roots(graph, roots)  # Must verify before pruning disconnected
        self._prune_disconnected_nodes(graph, roots)

        log.debug("Pruned graph G(V=%d, E=%d)", len(graph.nodes), len(graph.edges))

        packages = self._extract_packages(graph, parameters)

        if self.strict:
            self._verify_specified_packages(packages, parameters)

        return packages

    def _construct_graph(self, parameters: Parameters) -> Tuple[nx.DiGraph, Set[str]]:
        """Returns the main resolution graph and root nodes from given parameters.

        The resolution graph is a directed graph made of alternating levels of match
        specifications strings and conda package objects. The graph has multiple roots
        which are associated with the required match specification parameters. Starting
        from the roots, packages and their dependencies are recursively added to the
        graph unless a package is determined to be constrained via the parameters.
        """

        graph = nx.DiGraph()
        roots: Set[str] = set()

        # Note: for efficiently, use the specification strings (value) in the graph
        specs_to_process: Set[str] = set(req.value for req in parameters.requirements)
        specs_processed: Set[str] = set()

        for spec in specs_to_process:
            log.debug("Adding root node: %s", spec)
            graph.add_node(spec, root=True)
            roots.add(spec)

        while specs_to_process:
            spec = specs_to_process.pop()
            specs_processed.add(spec)
            log.debug("Processing spec %s", spec)

            for package in self._query_channel(spec, parameters):
                if parameters.is_constrained(package):
                    log.debug("Ignoring constrained package: %s", package)
                    continue

                if package not in graph:
                    graph.add_node(package)

                log.debug("Connecting spec %s to package %s", spec, package)
                graph.add_edge(spec, package)

                for depend in package.depends:
                    if depend not in graph:
                        graph.add_node(depend)

                    log.debug("Connecting package %s to spec %s", package, depend)
                    graph.add_edge(package, depend)

                    if depend not in specs_processed:
                        specs_to_process.add(depend)

        return graph, roots

    def _query_channel(
        self, spec: str, parameters: Parameters
    ) -> Iterator[CondaPackage]:
        """Yields conda package for the specified channel query."""
        yield from self.source.query_packages(spec, subdirs=parameters.subdirs)

    def _prune_unsatisfied_nodes(self, graph: nx.DiGraph) -> None:
        """Prune unsatisfied nodes - specification nodes with no successors."""
        log.debug("Pruning unsatisfied nodes")
        for node in set(graph):
            self._prune_unsatisfied_node(graph, node)

    def _prune_unsatisfied_node(self, graph: nx.DiGraph, node: Any) -> None:
        """Prune a single unsatisfied specification node."""

        if not isinstance(node, str):
            return
        if node not in graph:
            return
        if list(graph.successors(node)):
            return

        log.debug("Removing unsatisfied spec: %s", node)
        parents = list(graph.predecessors(node))
        graph.remove_node(node)

        for parent in parents:
            if parent not in graph:
                continue

            log.debug("Removing package with missing dependency: %s", parent)
            grandparents = list(graph.predecessors(parent))
            graph.remove_node(parent)

            for grandparent in grandparents:
                self._prune_unsatisfied_node(graph, grandparent)

    def _prune_disconnected_nodes(self, graph: nx.DiGraph, roots: Set[str]) -> None:
        """Prune disconnected nodes - nodes without a path to at least one root node."""

        connected = set()
        for root in roots:
            connected.update(nx.dfs_preorder_nodes(graph, root))

        disconnected = set(graph.nodes) - connected
        for node in disconnected:
            log.debug("Pruning disconnected node: %s", node)
            graph.remove_node(node)

    def _verify_roots(self, graph: nx.DiGraph, roots: Set[str]) -> None:
        """Verifies that the graph contains the specified root nodes."""
        missing = set(root for root in roots if root not in graph)
        if missing:
            raise UnsatisfiedRequirementsError(missing)

    def _verify_specified_packages(
        self, packages: Iterable[CondaPackage], parameters: Parameters
    ) -> None:
        """Verifies that all packages are specified as requirements."""
        names = set(package.name for package in packages)
        specified = set(req.name for req in parameters.requirements)
        unspecified = set()

        for name in names:
            if name not in specified:
                unspecified.add(name)

        if unspecified:
            raise UnspecifiedPackagesError(unspecified)

    def _extract_packages(
        self, graph: nx.DiGraph, parameters: Parameters
    ) -> Tuple[CondaPackage, ...]:
        """Extract conda packages from the resolution graph."""

        packages = set()
        package_names = set()

        for node in graph.nodes:
            if not isinstance(node, CondaPackage):
                continue

            package_names.add(node.name)
            if not parameters.is_disposable(node):
                packages.add(node)

        return tuple(packages)


class Parameters:
    """Defines the parameters used in package resolution."""

    def __init__(
        self,
        requirements: Iterable[str],
        exclusions: Iterable[str],
        disposables: Iterable[str],
        subdirs: Iterable[str],
    ) -> None:
        self._requirements = tuple(_make_specs(requirements))
        self._exclusions = tuple(_make_specs(exclusions))
        self._disposables = tuple(_make_specs(disposables))
        self._subdirs = tuple(subdirs)

        self._requirement_groups = groupby(self._requirements, lambda spec: spec.name)
        self._exclusion_groups = groupby(self._exclusions, lambda spec: spec.name)
        self._disposables_groups = groupby(self._disposables, lambda spec: spec.name)

    @property
    def requirements(self) -> Tuple[CondaSpecification, ...]:
        """Returns anaconda match specifications for required packages."""
        return self._requirements

    @property
    def subdirs(self) -> Tuple[str, ...]:
        """Returns the selected platform sub-directories."""
        return self._subdirs

    def is_constrained(self, package: CondaPackage) -> bool:
        """Returns True if a constrained (excluded from package resolution)."""

        requirements = self._requirement_groups.get(package.name, [])
        if not all(spec.match(package) for spec in requirements):
            return True

        exclusions = self._exclusion_groups.get(package.name, [])
        if any(spec.match(package) for spec in exclusions):
            return True

        return False

    def is_disposable(self, package: CondaPackage) -> bool:
        """Returns True if a disposable (removable after package resolution)."""
        disposables = self._disposables_groups.get(package.name, [])
        return any(disposable.match(package) for disposable in disposables)


class UnsatisfiedRequirementsError(CondaReplicateException):
    """Exception raised when required specifications could not be satisfied."""

    def __init__(self, missing: Iterable[str]) -> None:
        self.missing = sorted(missing)
        message = f"Missing required packages: {missing!r}"
        super().__init__(message)


class UnspecifiedPackagesError(CondaReplicateException):
    """Exception raised in strict mode when packages are not specified explicitly."""

    def __init__(self, unspecified: Iterable[str]) -> None:
        self.unspecified = sorted(unspecified)
        message = f"Unspecified packages: {unspecified!r}"
        super().__init__(message)


def _make_specs(specs: Iterable[str]) -> Iterator[CondaSpecification]:
    yield from (CondaSpecification(spec) for spec in specs)
