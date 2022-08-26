from __future__ import annotations

import conda.exceptions
import conda.exports

from conda_replicate import CondaReplicateException
from conda_replicate.adapters.package import CondaPackage


class CondaSpecification:
    def __init__(self, spec: str) -> None:
        try:
            self._internal = conda.exports.MatchSpec(spec)
        except conda.exceptions.InvalidVersionSpec as exception:
            raise InvalidCondaSpecification(exception)

    @classmethod
    def from_string(cls, value: str) -> CondaSpecification:
        # return cls(conda.exports.MatchSpec(value))
        pass

    @property
    def name(self) -> str:
        return self._internal.name

    @property
    def value(self) -> str:
        return self._internal.original_spec_str

    def match(self, package: CondaPackage) -> bool:
        # Note: Internal match uses package properties
        return self._internal.match(package)

    def __repr__(self):
        class_name = self.__class__.__name__
        return f"<{class_name}: value={self.value!r}>"


class InvalidCondaSpecification(CondaReplicateException):
    """Invalid match specification."""
