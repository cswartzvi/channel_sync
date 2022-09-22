from __future__ import annotations
from asyncio.log import logger

import logging
from typing import Any, Iterable, Iterator, List, Optional, Protocol, Set, Tuple

import networkx as nx

from conda_replicate import CondaReplicateException
from conda_replicate.adapters.channel import CondaChannel
from conda_replicate.adapters.package import CondaPackage
from conda_replicate.adapters.specification import CondaSpecification
from conda_replicate.adapters.subdir import get_default_subdirs
from conda_replicate.group import groupby

log = logging.getLogger(__name__)


def find_packages(
    channel: CondaChannel,
    requirements: Iterable[str],
    exclusions: Optional[Iterable[str]] = None,
    disposables: Optional[Iterable[str]] = None,
    subdirs: Optional[Iterable[str]] = None,
    latest: bool = False,
):
    exclusions = [] if exclusions is None else exclusions
    disposables = [] if disposables is None else disposables
    subdirs = get_default_subdirs() if subdirs is None else subdirs
    
    filters: List[_PackageFilter] = []
    if requirements:
        filters.append(_InclusionFilter(requirements))
    if exclusions:
        filters.append(_ExclusionFilter(exclusions))
    if latest:
        filters.append(_LatestVersionFilter(requirements))

    query = _PackageQuery(channel, subdirs, *filters)
    graph = create_dependency_graph(requirements, query)
    packages = extract_dependency_graph_packages(graph)

    if disposables:
        filter_ = _ExclusionFilter(disposables)
        packages = filter_(packages)

    return set(packages)


class _PackageQuery:
    def __init__(
        self, channel: CondaChannel, subdirs: Iterable[str], *filters: _PackageFilter
    ) -> None:
        self.channel = channel
        self.subdirs = tuple(subdirs)
        self.filters = filters

    def __call__(self, spec: str) -> Iterator[CondaPackage]:
        packages = self.channel.query_packages(spec, self.subdirs)
        for filter_ in self.filters:
            packages = filter_(packages)
        for package in packages:
            logger.debug("")
            yield package


class _PackageFilter(Protocol):
    def __call__(self, packages: Iterable[CondaPackage]) -> Iterator[CondaPackage]:
        ...


class _InclusionFilter:
    def __init__(self, specs: Iterable[str]) -> None:
        self.groups = groupby(_make_spec_objects(specs), lambda obj: obj.name)

    def __call__(self, packages: Iterable[CondaPackage]) -> Iterator[CondaPackage]:
        for package in packages:
            if all(obj.match(package) for obj in self.groups.get(package.name, [])):
                # NOTE: `all` returns True for an empty iterator
                logger.info("")
                yield package
            else:
                logger.debug("")


class _ExclusionFilter:
    def __init__(self, specs: Iterable[str]) -> None:
        self.groups = groupby(_make_spec_objects(specs), lambda obj: obj.name)

    def __call__(self, packages: Iterable[CondaPackage]) -> Iterator[CondaPackage]:
        for package in packages:
            if any(obj.match(package) for obj in self.groups.get(package.name, [])):
                # NOTE: `any` returns False for an empty iterator
                logger.info("")
                continue
            logger.debug("")
            yield package


class _LatestVersionFilter:

    def __init__(self, keep_specs: Optional[Iterable[str]] = None) -> None:
        keep_specs = [] if keep_specs is None else keep_specs
        self.groups = groupby(_make_spec_objects(keep_specs), lambda obj: obj.name)

    def __call__(self, packages: Iterable[CondaPackage]) -> Iterator[CondaPackage]:
        groups = groupby(packages, lambda pkg: pkg.name)
        for group in groups.values():
            version = max(group).version
            for package in group:
                if any(obj.match(package) for obj in self.groups.get(package.name, [])):
                    yield package
                elif package.version == version:
                    yield package


class _LatestBuildFilter:
    def __call__(self, packages: Iterable[CondaPackage]) -> Iterator[CondaPackage]:
        pass


def create_dependency_graph(specs: Iterable[str], query: _PackageQuery) -> nx.DiGraph:
    """Returns the main resolution graph and root nodes from given parameters.

    The resolution graph is a directed graph made of alternating levels of match
    specifications strings and conda package objects. The graph has multiple roots
    which are associated with the required match specification parameters. Starting
    from the roots, packages and their dependencies are recursively added to the
    graph unless a package is determined to be constrained via the parameters.
    """

    graph = nx.DiGraph()
    _populate_graph(graph, specs, query)
    log.info("Initial graph G(V%d, E=%d)", len(graph.nodes), len(graph.edges))
    _prune_unsatisfied_nodes(graph)
    _prune_disconnected_nodes(graph, specs)
    _verify_graph_requirements(graph, specs)
    log.info("Final graph G(V=%d, E=%d)", len(graph.nodes), len(graph.edges))
    return graph


def extract_dependency_graph_packages(graph: nx.DiGraph) -> Iterator[CondaPackage]:
    for node in graph.nodes:
        if isinstance(node, CondaPackage):
            yield node


def _populate_graph(
    graph: nx.DiGraph, specs: Iterable[str], query: _PackageQuery
) -> None:
    """Populate the dependency graph"""
    specs_to_process: Set[str] = set()
    specs_processed: Set[str] = set()

    for spec in specs:
        log.info("Adding root node: %s", spec)
        specs_to_process.add(spec)
        graph.add_node(spec, root=True)

    while specs_to_process:
        spec = specs_to_process.pop()
        specs_processed.add(spec)
        log.info("Processing spec %s", spec)

        for package in query(spec):

            if package not in graph:
                graph.add_node(package)

            log.info("Connecting spec %s to package %s", spec, package)
            graph.add_edge(spec, package)

            for depend in package.depends:
                if depend not in graph:
                    graph.add_node(depend)

                log.info("Connecting package %s to spec %s", package, depend)
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

        log.info("Removing unsatisfied spec: %s", node)
        parents = list(graph.predecessors(node))
        graph.remove_node(node)

        for parent in parents:
            if parent not in graph:
                continue

            log.info("Removing package with missing dependency: %s", parent)
            grandparents = list(graph.predecessors(parent))
            graph.remove_node(parent)

            for grandparent in grandparents:
                prune_unsatisfied(grandparent)

    log.info("Pruning unsatisfied nodes")
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
        log.info("Pruning disconnected node: %s", node)
        graph.remove_node(node)


def _verify_graph_requirements(graph: nx.DiGraph, specs: Iterable[str]) -> None:
    missing = set(spec for spec in specs if spec not in graph)
    if missing:
        raise UnsatisfiedRequirementsError(missing)


class Resolver:
    """Channel based package and dependency resolution."""

    _root_attribute = "root"

    def __init__(self, source: CondaChannel, latest: bool = False) -> None:
        self.source = source
        self.latest = latest

    def resolve(self, parameters: Parameters) -> Tuple[CondaPackage, ...]:
        """Execute the resolution algorithm using specified parameters."""

        graph, roots = self._construct_graph(parameters)

        log.debug("Initial graph G(V%d, E=%d)", len(graph.nodes), len(graph.edges))

        self._prune_unsatisfied_nodes(graph)

        self._verify_roots(graph, roots)  # Must verify before pruning disconnected

        self._prune_disconnected_nodes(graph, roots)

        log.debug("Pruned graph G(V=%d, E=%d)", len(graph.nodes), len(graph.edges))

        packages = self._extract_packages(graph, parameters)
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

        def constraint_filter(packages):
            for package in packages:
                if parameters.is_constrained(package):
                    log.debug("Ignoring constrained package: %s", package)
                    continue
                yield package

        packages = constraint_filter(
            self.source.query_packages(spec, subdirs=parameters.subdirs)
        )

        if not self.latest:
            yield from packages
        else:
            packages_by_name = groupby(packages, lambda pkg: pkg.name)
            for packages_for_name in packages_by_name.values():
                sorted_packages = sorted(packages_for_name)
                version = sorted_packages[-1].version
                packages_by_version = groupby(sorted_packages, lambda pkg: pkg.version)
                yield from packages_by_version[version]

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
        self._flat_requirements = tuple(_make_specs(requirements))
        self._requirements = groupby(self._flat_requirements, lambda spec: spec.name)
        self._exclusions = groupby(_make_specs(exclusions), lambda spec: spec.name)
        self._disposables = groupby(_make_specs(disposables), lambda spec: spec.name)
        self._subdirs = tuple(subdirs)

    @property
    def requirements(self) -> Tuple[CondaSpecification, ...]:
        """Returns anaconda match specifications for required packages."""
        return self._flat_requirements

    @property
    def subdirs(self) -> Tuple[str, ...]:
        """Returns the selected platform sub-directories."""
        return self._subdirs

    def is_constrained(self, package: CondaPackage) -> bool:
        """Returns True if a constrained (excluded from package resolution)."""

        requirements = self._requirements.get(package.name, [])
        if not all(spec.match(package) for spec in requirements):
            return True

        exclusions = self._exclusions.get(package.name, [])
        if any(spec.match(package) for spec in exclusions):
            return True

        return False

    def is_disposable(self, package: CondaPackage) -> bool:
        """Returns True if a disposable (removable after package resolution)."""
        disposables = self._disposables.get(package.name, [])
        return any(disposable.match(package) for disposable in disposables)


class UnsatisfiedRequirementsError(CondaReplicateException):
    """Exception raised when required specifications could not be satisfied."""

    def __init__(self, missing: Iterable[str]) -> None:
        self.missing = sorted(missing)
        message = f"Missing required packages: {missing!r}"
        super().__init__(message)


def _make_specs(specs: Iterable[str]) -> Iterator[CondaSpecification]:
    yield from (CondaSpecification(spec) for spec in specs)


def _make_spec_objects(specs: Iterable[str]) -> Iterator[CondaSpecification]:
    yield from (CondaSpecification(spec) for spec in specs)
