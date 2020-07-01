from __future__ import annotations
from typing import Iterable, List

from conda.exports import MatchSpec, VersionOrder


def create_spec(string: str) -> MatchSpec:
    """Converts Anaconda specification string into match specification object."""
    return MatchSpec(string)


def create_specs(strings: Iterable[str]) -> List[MatchSpec]:
    """Converts Anaconda specification strings into match specification objects."""
    return [create_spec(string) for string in strings]


def create_order(version: str) -> VersionOrder:
    """Converts Anaconda version string into version order object."""
    return VersionOrder(version)


def match_spec(name: str, version: str, spec: str) -> bool:
    """Attempts to match a Anaconda package specificaton.

    Args:
        name: Name of the Anaconda package.
        version: Version of the Anaconda package.
        specification: Anaconda package specification string.

    Returns:
        bool: True if the package specification matches the given package details.
    """
    matcher = MatchSpec(spec)
    if matcher.name == name:
        if match_version(version, matcher):
            return True
    return False


def match_specs(name: str, version: str, specs: Iterable[str]) -> bool:
    """Attempts to match any of multiple Anaconda package specifications.

    Note: If results are returned once the first match is found (builtin 'any').

    Args:
        name: Name of the Anaconda package.
        version: Version of Anaconda package.
        specs: Iterable of Anaconda package specification.

    Returns:
        bool: True if at least one of the package specifications matches the given
            package details.
    """
    return any(match_spec(name, version, spec) for spec in specs)


def match_version(version: str, spec: MatchSpec) -> bool:
    """Attempts to match a Anaconda version specificaton.

    Args:
        version: Version of the Anaconda package.
        spec: Anaconda version specification.

    Returns:
        bool: True if the version specification matches the given version.
    """
    # Note: MatchSpec.version is not defined if is_name_only_spec is
    # False, therefore is_name_only_spec must come first in the expression
    # and make use of short-circuit evaluation.
    return spec.is_name_only_spec or spec.version.match(version)


def match_versions(versions: Iterable[str], spec: MatchSpec) -> bool:
    """Attempts to match any of multiple Anaconda version specifications.

    Note: If results are returned once the first match is found (builtin 'any').

    Args:
        versions: An iterable of Anaconda package versions.
        spec: Anaconda version specification.

    Returns:
        bool: True if at least one of the version specifications matches the given version.
    """
    return any(match_version(version, spec) for version in versions)
