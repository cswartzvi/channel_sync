from __future__ import annotations

from typing import Any, Dict, List, Tuple

from conda.exports import PackageRecord as _PackageRecord
from pydantic import BaseModel, Field


class CondaPackage:

    __slots__ = {"_internal", "_key", "_hash"}

    def __init__(self, source: _PackageRecord) -> None:
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

    @classmethod
    def from_dict(cls, data: Dict) -> CondaPackage:
        source = _PackageRecord.from_objects(data)
        adapter = cls(source)
        return adapter

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
        return (
            f"<{class_name}: name={self.name!r}, version={self.version!r}, "
            f"build={self.build!r}, build_number={self.build_number!r}, "
            f"channel={self.channel!r}, subdir={self.subdir!r}>"
        )

    def __str__(self):
        return self.fn


class CondaPackage2(BaseModel):
    name: str
    version: str
    build: str
    build_number: int
    channel: str
    subdir: str
    fn: str
    url: str
    depends: Tuple[str, ...]
    license: str
    size: int
    sha256: str

    class Config:
        allow_mutation = False


Packages = Dict[str, Dict[str, Any]]


class PackageDataFile(BaseModel):
    packages: Packages
    conda_packages: Packages = Field(alias="conda.packages", default_factory=dict)
    removed: List[str]


class RepoData(PackageDataFile):
    info: Dict[str, str]
    version: int = Field(alias="repodata_version")


class PatchInstructions(PackageDataFile):
    revoke: List[str]
    version: int = Field(alias="patch_instructions_version")
