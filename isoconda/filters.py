""" Anaconda package filters.

Filter parameters are based on the Anaconda package version specifications. See the following:
https://docs.conda.io/projects/conda-build/en/latest/resources/package-spec.html#package-match-specifications).

"""
from __future__ import annotations
import collections
import itertools
from typing import (
    Dict,
    Iterable,
    Iterator,
    List,
    Mapping
)

from conda.models.match_spec import MatchSpec

from isoconda.models import RepoData, PackageRecord

PYTHON = 'python'


def include_packages(repodata: RepoData, strings: Iterable[str]) -> RepoData:
    if not strings:
        return repodata

    groups: Dict[str, List[PackageRecord]] = collections.defaultdict(list)

    for spec in get_specs(strings):
        for package in repodata.get(spec.name, []):
            if match_spec(package.name, package.version, spec):
                groups[spec.name].append(package)
    return RepoData(repodata.subdir, groups)


def exclude_packages(repodata: RepoData, strings: Iterable[str]) -> RepoData:
    specs = get_specs(strings)
    groups: Dict[str, Iterable[PackageRecord]] = dict(repodata.items())  # all packages

    for spec in specs:
        packages: List[PackageRecord] = []
        for package in groups.get(spec.name, []):
            if not match_spec(package.name, package.version, spec):
                packages.append(package)
        if packages:
            groups[spec.name] = packages
        else:
            groups.pop(spec.name, '')

    return RepoData(repodata.subdir, groups)


def restrict_python(repodata: RepoData, versions: Iterable[float]) -> RepoData:
    if not versions:
        return repodata

    specs = get_specs(f'{PYTHON} {version:0.1f}*' for version in versions)
    python_packages: List[PackageRecord] = []

    # Python interperters
    for package in repodata.get(PYTHON, []):
        if match_any_specs(package.name, package.version, specs):
            python_packages.append(package)

    # Python dependencies
    groups: Dict[str, List[PackageRecord]] = collections.defaultdict(list)
    for package in repodata.packages():
        passed = True
        for depend in get_specs(package.depends):
            if depend.name == PYTHON:
                # Note: depend.version is not defined if is_name_only_spec is False,
                # therefore is_name_only_spec must come first in the expression and
                # make use of short-circuit evaluation.
                passed = (depend.is_name_only_spec or
                         any(depend.version.match(version) for version in versions))
                break
        if passed:
            groups[package.name].append(package)

    if python_packages:
        groups.update({PYTHON: python_packages})

    return RepoData(repodata.subdir, groups)


def get_specs(strings: Iterable[str]) -> List[MatchSpec]:
    return [MatchSpec(string) for string in strings]


def match_spec(name: str, version: str, spec: str) -> bool:
    """Attempts to match a Anaconda package version specificaton.

    Args:
        name: Name of the Anaconda package.
        version: Version of the Anaconda package.
        specification: Anaconda package version specification string.

    Returns:
        bool: True if the package version specification matches the given package details.
    """
    matcher = MatchSpec(spec)
    if matcher.name == name:
        if (matcher.is_name_only_spec or
            matcher.version.match(version)):
            return True
    return False


def match_any_specs(name: str, version: str, specs: Iterable[str]) -> bool:
    """Attempts to match any of multiple Anaconda package version specifications.

    Note: If results are returned once the first match is found (builtin 'any').

    Args:
        name: Name of the Anaconda package.
        version: Version of Anaconda package.
        specs: Iterable of Anaconda package version specification strings.

    Returns:
        bool: True if at least one of the package version specifications matches the given
            package details.

    """
    return any(match_spec(name, version, spec) for spec in specs)