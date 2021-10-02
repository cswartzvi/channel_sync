# -*- coding: utf-8 -*-

from __future__ import annotations
import operator as op
import re
from typing import (
    Any,
    Callable,
    List,
    Pattern,
)
from typing_extensions import Final, Protocol

from isoconda.caching import CachedInstances
from isoconda.models import PackageRecord
from isoconda.version import VersionOrder


def compatible_release_operator(x, y):
    return op.ge(x, y) and x.startswith(VersionOrder(".".join(y.split(".")[:-1])))


class Matcher(Protocol):
    """Protocol for package specification matcher classes.

    Classes that implemented this protocol should provide a call method
    that will determine if a given package version and build match the
    characteristics supplied by the concrete class.
    """

    def __call__(self, version: str, build: str) -> bool:
        pass


class OperatorMatcher:
    """Package specification matcher based on relation operators."""

    def __init__(self, base: str, operator: Callable[[Any, Any], bool]):
        self._base = base
        self._base_order = VersionOrder(base)
        self._operator = operator

    def __call__(self, version: str, build: str) -> bool:
        # Note: build is ignored when matching with operators
        order = VersionOrder(version)
        return self._operator(order, self._base_order)

    def __repr__(self):
        name = self.__class__.__name__
        return f"{name}(base={self._base!r}, operator={self._operator!r})"


class PatternMatcher:
    """Package specification matcher based on regular expression matching."""

    def __init__(self, version: str, build: str):
        self._version_regexp = self._process_pattern(version)
        self._build_regexp = self._process_pattern(build)

    def _process_pattern(self, pattern: str) -> Pattern:
        if pattern:
            processed = re.escape(pattern).replace("\\*", ".*")
        else:
            processed = r".*"
        return re.compile(processed)

    def __call__(self, version: str, build: str) -> bool:
        return (
            self._version_regexp.search(version) is not None
            and self._build_regexp.search(build) is not None
        )

    def __repr__(self):
        name = self.__class__.__name__
        return f"{name}(pattern={self._pattern!r})"


class MatchSpec(metaclass=CachedInstances):
    """Represents a single instance of an Anaconda package match specification.

    A match specification can consist of three parts:
    1. The first part is always the exact name of the package.
    2. The second part refers to the version anf may contain the following special
       characers:
        - | means OR
        - * matches 0 or more characters in the version string
        - <, >, <=, >=, == and != are relational operators on versions. == and != are exact.
          See https://www.python.org/dev/peps/pep-0440/ for more details.
        - ~=
        - , means AND (as higher precedence than |)
    3. The third part is always the exact build string. If there are 3 parts the
       second part must be the exact version.

    Note: Conda parses the version by splitting it into parts separated by |. If the part
    begins with <, >, =, or !, it is parsed as a relational operator. Otherwise, it is parsed
    as a version, possibly containing the "*" operator.

    See the Anaconda package match specifications for more details:
    https://docs.conda.io/projects/conda/en/latest/user-guide/concepts/pkg-specs.html#package-match-specifications  # noqa

    """

    VALID_VERSION: Final = re.compile(r"^[*.+!_0-9a-zA-Z]+$")

    OPERATORS: Final = {
        "<=": op.le,
        "<": op.lt,
        "==": op.eq,
        "=": op.eq,
        "!=": op.ne,
        ">=": op.ge,
        ">": op.gt,
        "~=": compatible_release_operator,
    }

    def __init__(self, name: str, version: str = "", build: str = ""):
        self._name = name
        self._version = version.replace("_", ".").replace("-", ".")
        self._build = build

        self._matchers: List[List[Matcher]] = []
        for outer in self._version.strip().split("|"):  # 'or' blocks
            if not outer:
                # split uses a different algorithm when a separator is supplied
                continue
            self._matchers.append([])
            for inner in outer.strip().split(","):  # 'and' blocks, higher precedence
                matcher = self._create_matcher(inner, build)
                self._matchers[-1].append(matcher)

    @classmethod
    def from_spec_string(cls, spec: str):
        split = [item.strip() for item in spec.split()]
        length = len(split)
        name = split[0]
        version = split[1] if length == 2 else ""
        build = split[2] if length == 3 else ""
        if length > 3:
            raise ValueError("Invalid match specification string.")

        return cls(name, version, build)

    @property
    def build(self) -> str:
        """The build string of the package."""
        return self._build

    @property
    def name(self) -> str:
        """The name of the package."""
        return self._name

    @property
    def version(self) -> str:
        """The package version."""
        return self._version

    def match(self, name: str, version: str, build: str) -> bool:
        if name != self.name:
            return False
        if self._matchers:
            return any(
                all(matcher(version, build) for matcher in group)
                for group in self._matchers
            )
        return True  # no matchers were specified

    def match_package(self, package: PackageRecord):
        return self.match(package.name, package.version, package.build)

    def _create_matcher(self, version: str, build: str) -> Matcher:
        for label, operator in self.OPERATORS.items():
            if version.startswith(label):
                if build:
                    raise ValueError(
                        "build string can only be supplied with exact version"
                    )
                if version[-2:] == ".*":
                    version = version[:-2]  # remove redundant '.*'
                elif version[-1:] == "*":
                    version = version[:-1]  # remove redundant '*'
                if "*" in version:
                    raise ValueError(
                        f'cannot use wildcard "*" with relational operators {version}'
                    )
                label_length = len(label)
                extracted = version[label_length:]
                self._validate_version(extracted)
                return OperatorMatcher(extracted, operator)

        self._validate_version(version)
        return PatternMatcher(version, build)

    def _validate_version(self, version: str):
        if self.VALID_VERSION.search(version) is None:
            raise ValueError(f"invalid version character(s) {version}")

    def __repr__(self):
        name = self.__class__.__name__
        return f"{name}(name={self.name!r}, version={self.version!r}, build={self.build!r})"
