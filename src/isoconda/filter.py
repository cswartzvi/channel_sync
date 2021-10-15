from collections import defaultdict
from typing import Dict, Iterator, Mapping, Set, Tuple

from isoconda._typing import Grouping
from isoconda.match import MatchSpec
from isoconda.models import PackageRecord


class DependencyNotSatisfied(Exception):
    def __init__(self, spec: MatchSpec) -> None:
        self.spec = spec


def extract_dependencies(
    selected: Grouping[PackageRecord], pool: Grouping[PackageRecord]
) -> Grouping[PackageRecord]:

    dependencies: Dict[str, Set[PackageRecord]] = defaultdict(set)
    processed_dependencies = set()

    def walk_dependencies(package: PackageRecord) -> Iterator[PackageRecord]:
        for depend in package.depends:
            if depend in processed_dependencies:
                continue

            processed_dependencies.add(depend)
            spec = MatchSpec.from_spec_string(depend)

            packages = pool.get(spec.name, [])
            found = False
            for package in packages:
                if spec.match_package(package):
                    found = True
                    yield package
                    yield from walk_dependencies(package)

            if not found:
                raise DependencyNotSatisfied(spec)

    for _, group in selected.items():
        for package in group:
            try:
                for dependency in walk_dependencies(package):
                    dependencies[dependency.name].add(dependency)
            except DependencyNotSatisfied as e:
                print(
                    "Could not satisfied '{}' for {}: {} {} {}".format(
                        e.spec.spec_string,
                        package.name,
                        package.version,
                        package.build,
                        package.build_number,
                    )
                )

    return dependencies


def merge_package_groups(
    *groups: Grouping[PackageRecord],
) -> Grouping[PackageRecord]:
    results: Dict[str, Set[PackageRecord]] = defaultdict(set)
    for group in groups:
        for name, packages in group.items():
            results[name].update(packages)
    return results


def partition_packages(
    groups: Grouping[PackageRecord], specs: Grouping[MatchSpec]
) -> Tuple[Grouping[PackageRecord], Grouping[PackageRecord]]:

    matches = defaultdict(set)
    remaining = defaultdict(set)
    for name, group in groups.items():
        match_spec = specs.get(name, None)
        if match_spec is None:
            remaining[name] = set(group)
            continue
        for package in group:
            if any(spec.match_package(package) for spec in specs[name]):
                matches[name].add(package)
            else:
                remaining[name].add(package)
    return matches, remaining
