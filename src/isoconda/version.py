# -*- coding: utf-8 -*-

from __future__ import annotations
from itertools import zip_longest
import re
from typing import Any, Final, List, Tuple


class VersionOrder:
    """
    This class implements an order relation between anaconda version strings.

    See the official version ordering specification provided by anaconda:
    Note: https://docs.conda.io/projects/conda/en/latest/user-guide/concepts/pkg-specs.html#version-ordering  # noqa

    Most of this class was lifted from the official conda project because recent versions
    of conda are not available on PYPI - and vendoring the entire conda package is not appealing.
    See github for more details (licensed as BSD-3-Clause):
    https://github.com/conda/conda/blob/master/conda/models/version.py

    Args:
        spec: The version specification string.
    """

    FILL_VALUE: Final = 0
    COMPONENT_SPLIT: Final = re.compile("([0-9]+|[*]+|[^0-9*]+)")

    def __init__(self, spec: str):
        self._spec = spec
        self._version, self._local = self._parse_specs(spec)

    def _parse_specs(self, spec: str) -> Tuple[List[str], List[str]]:
        """Splits the version specification into version number and local version number.

        Note: the (non-local) version number contains the version epoch (see the anaconda
        version order specification for more details).
        """
        spec = spec.strip().lower()
        if not spec:
            raise ValueError("empty version specification")

        # Note: The epoch version must be a string initially (see processing below).
        epoch: List[Any] = ["0"]
        *leading, last = spec.split("!")
        if leading:
            if len(leading) > 1:
                raise ValueError("duplicate epoch separator '!'")
            if not leading[0].isnumeric():
                raise ValueError(spec, "epoch must be an integer")
            epoch = [leading[0]]

        local = []
        first, *remaining = last.split("+")
        if remaining:
            if len(remaining) > 1:
                raise ValueError("duplicate local version separator '+'")
            local = first.split(".")

        version: List[Any] = epoch + first.split(".")

        # Each section of the version specification is initially made up of multiple
        # components split from above. However, these component may contain additional
        # sub-components identified by numerals and non-numerals. Numerals should be
        # converted to integers. Special strings are also handled here.
        for section in (version, local):
            for k in range(len(section)):
                components = self.COMPONENT_SPLIT.findall(section[k])
                if not components:
                    raise ValueError("empty version component")
                for j in range(len(components)):
                    if components[j].isdigit():
                        components[j] = int(components[j])
                    elif components[j] == "post":
                        # Ensure number < 'post' == infinity
                        components[j] = float("inf")
                    elif components[j] == "dev":
                        # Ensure '*' < 'DEV' < '_' < 'a' < number by upper-casing,;
                        # note that all other strings are lower case.
                        components[j] = "DEV"
                if section[k][0].isdigit():
                    section[k] = components
                else:
                    # Components shall start with a number to keep numbers and
                    # strings in phase => prepend fillvalue
                    section[k] = [self.FILL_VALUE] + components

        return version, local

    def _eq(self, section1, section2):
        for comp1, comp2 in zip_longest(section1, section2, fillvalue=[]):
            for sub1, sub2 in zip_longest(comp1, comp2, fillvalue=self.FILL_VALUE):
                if sub1 != sub2:
                    return False
        return True

    def __ne__(self, other):
        return not (self == other)

    def __eq__(self, other):
        if not isinstance(other, VersionOrder):
            return False
        return self._eq(self._version, other._version) and self._eq(
            self._local, other._local
        )

    def __lt__(self, other: VersionOrder):
        for sec1, sec2 in zip(
            [self._version, self._local], [other._version, other._local]
        ):
            for comp1, comp2 in zip_longest(sec1, sec2, fillvalue=[]):
                for sub1, sub2 in zip_longest(comp1, comp2, fillvalue=self.FILL_VALUE):
                    if sub1 == sub2:
                        continue
                    elif isinstance(sub1, str):
                        if not isinstance(sub2, str):
                            # str < int
                            return True
                    elif isinstance(sub2, str):
                        # not (int < str)
                        return False
                    # sub1 and sub2 have the same type
                    return sub1 < sub2
        # self == other
        return False

    def __ge__(self, other):
        return not (self < other)

    def __gt__(self, other):
        return other < self

    def __le__(self, other):
        return not (other < self)

    def __repr__(self):
        return f"{type(self).__name__}(spec={self._spec!r})"

    def __str__(self):
        return self._spec
