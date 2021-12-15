from typing import Iterable, Iterator, Set, Tuple

import networkx as nx

from isoconda.grouping import Grouping, group_by
from conda.exports import MatchSpec, PackageRecord


def solve(
    specs: Iterable[MatchSpec], packages: Iterable[PackageRecord]
) -> Set[PackageRecord]:
    """[summary]

    Args:
        specs (Iterable[MatchSpec]): [description]
        packages (Iterable[PackageRecord]): [description]

    Returns:
        Set[PackageRecord]: [description]
    """
    packages_by_name = group_by(packages, lambda pkg: pkg.name)
    specs_by_name = group_by(specs, lambda spec: spec.name)
    candidates, graph = find_candidates(specs, packages_by_name, specs_by_name)
    _prune_candidates(candidates, graph)
    return candidates


def find_candidates(
    specs: Iterable[MatchSpec],
    records: Grouping[str, PackageRecord],
    constraints: Grouping[str, MatchSpec],
) -> Tuple[Set[PackageRecord], nx.DiGraph]:
    """[summary]

    Args:
        specs: Match specification object, grouped by package name, used to
            identify potential candidates.
        records: Package records, grouped by package name, from which candidates
            will be identified.
        constraints: Match specification objects, grouped by package
            name, that will further constrain potential package records.

    Returns:
        A tuple of candidate package records and a directed graph of package
        record and match specification objects.
    """
    graph = nx.DiGraph()
    candidates: Set[PackageRecord] = set()
    processed_specs: Set[MatchSpec] = set()
    unprocessed_specs: Set[MatchSpec] = set(specs)

    while unprocessed_specs:
        temp_specs: Set[MatchSpec] = set()
        for spec in unprocessed_specs:
            for record in match_records(spec, records, constraints):
                candidates.add(record)
                graph.add_edge(spec, record)
                for dependency in get_dependencies(record):
                    temp_specs.add(dependency)
                    graph.add_edge(record, dependency)
        unprocessed_specs = temp_specs.difference(processed_specs)
        processed_specs.update(temp_specs)

    return candidates, graph


def get_dependencies(record: PackageRecord) -> Iterator[MatchSpec]:
    """Yields match specification objects for the dependencies of a package record.

    Args:
        record: Package records from which match specification dependencies
            will be generated.
    """
    yield from (MatchSpec(depend) for depend in record.depends)


def match_records(
    spec: MatchSpec,
    records: Grouping[str, PackageRecord],
    constraints: Grouping[str, MatchSpec],
) -> Iterator[PackageRecord]:
    """Yields package records matches under specified constraints.

    Args:
        spec: Match specification object used to identify potentail matches.
        records: Package records, grouped by name, from which matches
            will be found.
        constraints: Match specification objects, grouped by package
            name, that will further constrain potential package records.
    """
    constraints_for_name = constraints.get(spec.name, [])
    for record in records.get(spec.name, []):
        if not spec.match(record):
            continue
        if all(const.match(record) for const in constraints_for_name):
            yield record  # `all` is True for empty iterable


def _prune_candidates(candidates: Set[PackageRecord], graph: nx.DiGraph):
    """Updates candidates by pruning unsatisfiable candidate records."""
    for node in list(graph.nodes):
        if node not in graph.nodes:
            continue  # already removed
        if graph.out_degree(node) > 0:
            continue  # not a leaf
        if not isinstance(node, MatchSpec):
            continue  # not a match specification
        _prune_unsatisfied(node, candidates, graph)


def _prune_unsatisfied(
    spec: MatchSpec, candidates: Set[PackageRecord], graph: nx.DiGraph
):
    """Updates candidates by pruning unsatisfied specifications recursively."""
    for pred_record in list(graph.predecessors(spec)):
        if pred_record not in graph.nodes:
            continue  # already removed
        candidates.remove(pred_record)
        graph.remove_edge(pred_record, spec)
        _prune_orphaned(pred_record, candidates, graph)
        for pred_spec in list(graph.predecessors(pred_record)):
            if pred_spec not in graph.nodes:
                continue  # already removed
            graph.remove_edge(pred_spec, pred_record)
            if graph.out_degree(pred_spec) == 0:
                _prune_unsatisfied(pred_spec, candidates, graph)
        graph.remove_node(pred_record)
    if spec in graph.nodes:
        graph.remove_node(spec)


def _prune_orphaned(
    record: PackageRecord, candidates: Set[PackageRecord], graph: nx.DiGraph
):
    """Updates candidates by identifying and removing orphaned package records and
    dependencies."""
    for child_spec in list(graph.successors(record)):
        if child_spec not in graph.nodes:
            continue  # already removed
        graph.remove_edge(record, child_spec)
        if graph.in_degree(child_spec) > 0:
            continue  # not orphaned, dependencies of another package
        for child_record in list(graph.successors(child_spec)):
            if child_record not in graph.nodes:
                continue
            graph.remove_edge(child_spec, child_record)
            if graph.in_degree(child_record) > 0:
                continue  # not orphaned, satisfies another specification
            _prune_orphaned(child_record, candidates, graph)
            candidates.remove(child_record)
            graph.remove_node(child_record)
        if child_spec in graph.nodes:
            graph.remove_node(child_spec)
