from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Iterable, Iterator, Optional, Set, Tuple

import networkx as nx

from conda_local import CondaLocalException
from conda_local.group import groupby
from conda_local.adapters.channel import CondaChannel
from conda_local.adapters.package import CondaPackage
from conda_local.adapters.specification import CondaSpecification

log = logging.getLogger(__name__)


@dataclass
class ResolvedPackages:
    to_add: Set[CondaPackage] = field(default_factory=set)
    to_remove: Set[CondaPackage] = field(default_factory=set)


def resolve_packages(
    channel: CondaChannel,
    requirements: Iterable[str],
    exclusions: Iterable[str],
    disposables: Iterable[str],
    subdirs: Iterable[str],
    target: Optional[CondaChannel] = None,
    latest: bool = True,
    validate: bool = True,
) -> ResolvedPackages:
    """Performs package resolution on an anaconda channel based on specified parameters.

    Args:
        channel:
        requirements: An iterable of anaconda match specifications that defined the
            requirements of package resolution - which packages should be included
            and what versions / builds of those packages are allowed. Package
            resolution is designed to be a selective process, so if a particular
            package does note match a requirement (example: package 'A v0.2' does
            not match 'A >=1.0') then it will not be included in the solution.
        constraints (optional): An iterable of anaconda match specifications that
            defined additional constraints on package resolution. Constraints are
            permissive, meaning that a candidate is considered unconstrained if there
            are no match specifications for the package type in question. However,
            if one or more match specification exists for a candidate that package
            is considered constrained if it fails to match any of the specifications.
        subdirs (optional): Platform sub-directories where package resolution should
            take place. If None, then all default
        target (optional):
        validate (optional): Determines if the package resolution process must find
            at least on package for all specified requirements.
        latest:

    Returns:
        The results of package resolution in the form of a tuple of package record
        adapter objects.
    """

    parameters = Parameters(
        requirements=[CondaSpecification(spec) for spec in requirements],
        exclusions=[CondaSpecification(spec) for spec in exclusions],
        disposables=[CondaSpecification(spec) for spec in disposables],
        subdirs=subdirs
    )
    resolver = Resolver(channel, validate, latest)
    packages = set(resolver.resolve(parameters))

    if target is None or not target.is_queryable:
        results = ResolvedPackages(to_add=packages)
    else:
        existing_packages = set(target.iter_packages(subdirs))
        to_add = packages - existing_packages
        to_remove = existing_packages - packages
        results = ResolvedPackages(to_add=to_add, to_remove=to_remove)

    return results


class Resolver:
    """Channel based package and transitive dependency resolution."""

    def __init__(
        self, channel: CondaChannel, validate: bool = True, latest: bool = True
    ) -> None:
        self.channel = channel
        self.validate = validate
        self.latest = latest

    def resolve(self, parameters: Parameters) -> Tuple[CondaPackage, ...]:

        graph = self._construct_graph(parameters)

        log.debug("Initial graph G(V%d, E=%d)", len(graph.nodes), len(graph.edges))

        for node in set(graph):
            self._prune_unsatisfied_node(graph, node)

        for node in set(graph):
            self._prune_orphaned_node(graph, node)

        log.debug("Final graph G(V=%d, E=%d)", len(graph.nodes), len(graph.edges))

        packages = self._extract_packages(graph, parameters)
        return packages

    def _construct_graph(self, parameters: Parameters) -> nx.DiGraph:
        # The resulting graph is made of alternating levels of match specifications
        # packages; starting from the root requirement specifications and expanded,
        # transitively, through candidate packages and dependencies.

        graph = nx.DiGraph()

        # Note: for efficiently, we only story the specification strings in the graph
        specs_to_process: Set[str] = set(req.value for req in parameters.requirements)
        specs_processed: Set[str] = set()

        for spec in specs_to_process:
            log.debug("Adding root node: %s", spec)
            graph.add_node(spec, root=True)

        while specs_to_process:
            spec = specs_to_process.pop()
            specs_processed.add(spec)
            log.debug("Processing spec %s", spec)

            for package in self._query_channel(spec, parameters):
                if parameters.is_constrained(package):
                    log.debug("Ignoring constrained package: %s", package)
                    continue

                if package not in graph:
                    log.debug("Adding package node: %s", package)
                    graph.add_node(package)

                log.debug("Connecting spec %s to package %s", spec, package)
                graph.add_edge(spec, package)

                for depend in package.depends:
                    if depend not in graph:
                        log.debug("Adding spec node: %s", depend)
                        graph.add_node(depend)

                    log.debug("Connecting package %s to spec %s", package, depend)
                    graph.add_edge(package, depend)

                    if depend not in specs_processed:
                        specs_to_process.add(depend)

        return graph

    def _query_channel(
        self, spec: str, parameters: Parameters
    ) -> Iterator[CondaPackage]:
        yield from self.channel.query_packages(
            spec, subdirs=parameters.subdirs, latest=self.latest
        )

    def _prune_unsatisfied_node(self, graph: nx.DiGraph, node: Any) -> None:
        # Unsatisfied nodes are spec nodes with no successors (satisfying packages).

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

    def _prune_orphaned_node(self, graph: nx.DiGraph, node: Any):
        # Orphaned nodes have no predecessors (excludes root nodes).

        if node not in graph:
            return
        if graph.nodes[node].get("root", False):
            return
        if list(graph.predecessors(node)):
            return

        log.debug("Removing orphaned node: %s", node)
        children = list(graph.successors(node))
        graph.remove_node(node)

        for child in children:
            self._prune_orphaned_node(graph, child)

    def _extract_packages(
        self, graph: nx.DiGraph, parameters: Parameters
    ) -> Tuple[CondaPackage, ...]:

        packages = set()
        package_names = set()
        required_package_names = set(spec.name for spec in parameters.requirements)

        for node in graph.nodes:
            if not isinstance(node, CondaPackage):
                continue

            package_names.add(node.name)
            if not parameters.is_disposable(node):
                packages.add(node)

        if self.validate:
            missing = required_package_names - package_names
            if missing:
                raise UnsatisfiedRequirementsError(missing)

        return tuple(packages)


class Parameters:
    """Defines the match specification parameters used in package resolution."""

    def __init__(
        self,
        requirements: Iterable[CondaSpecification],
        exclusions: Iterable[CondaSpecification],
        disposables: Iterable[CondaSpecification],
        subdirs: Iterable[str],
    ) -> None:
        self._flat_requirements = tuple(requirements)
        self._requirements = groupby(requirements, lambda spec: spec.name)
        self._exclusions = groupby(exclusions, lambda spec: spec.name)
        self._disposables = groupby(disposables, lambda spec: spec.name)
        self._subdirs = tuple(subdirs)

    @property
    def requirements(self) -> Tuple[CondaSpecification, ...]:
        return self._flat_requirements

    @property
    def subdirs(self) -> Tuple[str, ...]:
        return self._subdirs

    def is_constrained(self, package: CondaPackage) -> bool:
        requirements = self._requirements.get(package.name, [])
        if not all(spec.match(package) for spec in requirements):
            return True

        exclusions = self._exclusions.get(package.name, [])
        if any(spec.match(package) for spec in exclusions):
            return True

        return False

    def is_disposable(self, package: CondaPackage) -> bool:
        disposables = self._disposables.get(package.name, [])
        return any(disposable.match(package) for disposable in disposables)


class UnsatisfiedRequirementsError(CondaLocalException):
    def __init__(self, missing: Iterable[str]) -> None:
        self.missing = sorted(missing)
        message = f"Missing required packages: {missing!r}"
        super().__init__(message)
