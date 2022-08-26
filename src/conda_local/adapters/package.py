from __future__ import annotations

from typing import Dict, Tuple

import conda.exports


class CondaPackage:

    __slots__ = {"_internal", "_key", "_hash"}

    def __init__(self, source: conda.exports.PackageRecord) -> None:
        self._internal = source

        # Equality / hash key should NOT include channel
        self._key = (
            self.subdir,
            self.name,
            self.version,
            self.build_number,
            self.build,
        )

        self._hash = hash(self._key)

    @property
    def build(self) -> str:
        return self._internal.build

    @property
    def build_number(self) -> int:
        return self._internal.build_number

    @property
    def channel(self) -> str:
        return self._internal.channel.canonical_name

    @property
    def depends(self) -> Tuple[str, ...]:
        return self._internal.depends

    @property
    def fn(self) -> str:
        return self._internal.fn

    @property
    def license(self) -> str:
        return self._internal.license

    @property
    def name(self) -> str:
        return self._internal.name

    @property
    def size(self) -> int:
        return self._internal.size

    @property
    def sha256(self) -> str:
        return self._internal.sha256

    @property
    def subdir(self) -> str:
        return self._internal.subdir

    @property
    def url(self) -> str:
        return self._internal.url

    @property
    def version(self) -> str:
        return self._internal.version

    def dump(self) -> Dict:
        return self._internal.dump()

    def __hash__(self):
        return self._hash

    def __eq__(self, other):
        return self._key == other._key

    def __repr__(self):
        class_name = self.__class__.__name__
        text = f"<{class_name}: " + ", ".join(
            f"{key}: {getattr(self, key)}"
            for key, value in CondaPackage.__dict__.items()
            if isinstance(value, property)
        )
        return text

    def __str__(self):
        return self.fn
