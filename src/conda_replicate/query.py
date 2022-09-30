from __future__ import annotations

import logging
from typing import Iterable, Iterator, Optional, Protocol

from conda_replicate.adapters.channel import CondaChannel
from conda_replicate.adapters.package import CondaPackage
from conda_replicate.adapters.specification import CondaSpecification
from conda_replicate.group import groupby

logger = logging.getLogger(__name__)


class PackageQuery(Protocol):
    def __call__(self, spec: str) -> Iterator[CondaPackage]:
        ...


class PackageFilter(Protocol):
    def __call__(self, packages: Iterable[CondaPackage]) -> Iterator[CondaPackage]:
        ...


def crate_package_query(
    channel: CondaChannel, subdirs: Iterable[str], *filters: PackageFilter
) -> PackageQuery:
    def query(spec: str) -> Iterator[CondaPackage]:
        packages = channel.query_packages(spec, subdirs)
        for filter_ in filters:
            packages = filter_(packages)
        for package in packages:
            logger.debug("")
            yield package

    return query


class InclusionFilter:
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


class ExclusionFilter:
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


class LatestVersionFilter:
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


class LatestBuildFilter:
    def __init__(self, keep_specs: Optional[Iterable[str]] = None) -> None:
        keep_specs = [] if keep_specs is None else keep_specs
        self.groups = groupby(_make_spec_objects(keep_specs), lambda obj: obj.name)

    def __call__(self, packages: Iterable[CondaPackage]) -> Iterator[CondaPackage]:
        groups = groupby(packages, lambda pkg: (pkg.name, pkg.version, pkg.depends))
        for group in groups.values():
            timestamp = max(group, key=lambda pkg: pkg.timestamp).timestamp
            for package in group:
                if any(obj.match(package) for obj in self.groups.get(package.name, [])):
                    yield package
                elif package.timestamp == timestamp:
                    yield package


def _make_spec_objects(specs: Iterable[str]) -> Iterator[CondaSpecification]:
    yield from (CondaSpecification(spec) for spec in specs)
