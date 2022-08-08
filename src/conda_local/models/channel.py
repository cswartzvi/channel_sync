from __future__ import annotations

import hashlib
import json
import tarfile
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Tuple

import fsspec
import conda_build.api
from conda.api import SubdirData as _SubdirData
from conda.exports import Channel as _Channel
from pydantic import BaseModel, Field

from conda_local import CondaLocalException
from conda_local.group import groupby
from conda_local.models import get_known_subdirs
from conda_local.models.package import CondaPackage

_PATCH_GENERATOR_FILE = "patch_generator.tar.bz2"
_PATCH_INSTRUCTIONS_FILE = "patch_instructions.json"
_REPODATA_FILE = "repodata.json"

PackageDict = Dict[str, Dict[str, Any]]


class BadPackageDownload(CondaLocalException):
    pass


class CondaContainer:
    def __init__(self, url: str) -> None:
        self._url = url
        self._mapper = fsspec.get_mapper(url)

    @property
    def url(self) -> str:
        return self._url

    def find_subdirs(self) -> Tuple[str, ...]:
        found_subdirs = []
        for subdir in get_known_subdirs():
            if self._mapper.fs.exists(self._urlpath(self.url, subdir)):
                found_subdirs.append(subdir)
        return tuple(found_subdirs)

    def add_package(self, package: CondaPackage) -> None:
        if self.contains_package(package):
            contents = self._read_file(package.subdir, package.fn)
            if hashlib.sha256(contents).hexdigest() == package.sha256:
                return

        with fsspec.open(package.url, "rb") as fp:
            contents = fp.read()

        if len(contents) != package.size:
            raise BadPackageDownload(f"{package.fn} has incorrect size")
        if package.sha256 != hashlib.sha256(contents).hexdigest():
            raise BadPackageDownload(f"{package.fn} has incorrect sha256")

        self._write_file(package.subdir, package.fn, contents)

    def remove_package(self, package: CondaPackage) -> None:
        self._remove_file(package.subdir, package.fn)

    def contains_package(self, package: CondaPackage) -> bool:
        return self._contains_file(package.subdir, package.fn)

    def read_patch_instructions(self, subdir: str) -> PatchInstructions:
        contents = self._read_file(subdir, _PATCH_INSTRUCTIONS_FILE, b"{}")
        instructions = PatchInstructions.parse_raw(contents)
        return instructions

    def write_instructions(self, subdir: str, instructions: PatchInstructions) -> None:
        contents = json.dumps(instructions.dict(by_alias=True), indent=2)
        self._write_file(subdir, _PATCH_INSTRUCTIONS_FILE, contents.encode("utf-8"))

    def read_repodata(self, subdir: str) -> RepoData:
        contents = self._read_file(subdir, _REPODATA_FILE, b"{}")
        repodata = RepoData.parse_raw(contents)
        return repodata

    def write_repodata(self, subdir: str, repodata: RepoData) -> None:
        contents = json.dumps(repodata.dict(by_alias=True), indent=2)
        self._write_file(subdir, _REPODATA_FILE, contents.encode("utf-8"))

    def _read_file(
        self, subdir: str, filename: str, default: Optional[bytes] = None
    ) -> bytes:
        urlpath = self._urlpath(subdir, filename)
        if default is None:
            contents = self._mapper[urlpath]
        else:
            contents = self._mapper.get(urlpath, default)
        return contents

    def _write_file(self, subdir: str, filename: str, contents: bytes) -> None:
        urlpath = self._urlpath(subdir, filename)
        self._mapper[urlpath] = contents

    def _remove_file(self, subdir: str, filename: str) -> None:
        urlpath = self._urlpath(subdir, filename)
        del self._mapper[urlpath]

    def _contains_file(self, subdir: str, filename: str) -> bool:
        urlpath = self._urlpath(subdir, filename)
        return urlpath in self._mapper

    def _urlpath(self, *parts: str) -> str:
        return "/".join(parts)


class LocalCondaContainer(CondaContainer):
    def __init__(self, path: Path) -> None:
        self._path = path
        super().__init__(path.as_uri())

    @property
    def path(self) -> Path:
        return self._path

    @property
    def _patch_generator(self) -> Path:
        return self._path / _PATCH_GENERATOR_FILE

    def update_index(self) -> None:
        generator = self._path / _PATCH_GENERATOR_FILE
        conda_build.api.update_index(
            self._path, patch_generator=generator, progress=True
        )
        self._purge_packages()

    def _purge_packages(self) -> None:
        for subdir in self.find_subdirs():
            repodata = self.read_repodata(subdir)
            for filename in repodata.removed:
                self._remove_file(subdir, filename)

    def write_patch_generator(self) -> None:
        generator = self._patch_generator
        generator.parent.mkdir(exist_ok=True, parents=True)
        with tarfile.open(generator, "w:bz2") as tar:
            for instructions in self._path.glob("**/" + _PATCH_INSTRUCTIONS_FILE):
                tar.add(instructions, arcname=instructions.relative_to(self._path))


class CondaChannel(CondaContainer):
    def __init__(self, source: str) -> None:
        source = source.replace("\\", "/")
        self._internal = _Channel(source)
        super().__init__(self._internal.base_url)

    @property
    def name(self) -> str:
        return self._internal.canonical_name

    def iter_packages(self, subdirs: Iterable[str]) -> Iterator[CondaPackage]:
        return self.query_packages("*", subdirs=subdirs)

    def query_packages(
        self, spec: str, subdirs: Iterable[str], latest: bool = False
    ) -> Iterator[CondaPackage]:
        query = _SubdirData.query_all(spec, channels=[self._internal], subdirs=subdirs)
        packages = (CondaPackage(package) for package in query)

        if latest:
            groups = groupby(packages, lambda pkg: (pkg.name, pkg.version, pkg.depends))
            for group in groups.values():
                group = sorted(group, key=lambda pkg: (pkg.build, pkg.build_number))
                yield group[-1]
        else:
            yield from packages

    def __repr__(self):
        class_name = self.__class__.__name__
        return f"<{class_name}: url={self.url!r}>"


class RepoData(BaseModel):
    info: Dict[str, str] = Field(default_factory=dict)
    packages: PackageDict = Field(default_factory=dict)
    conda_packages: PackageDict = Field(alias="conda.packages", default_factory=dict)
    removed: List[str] = Field(default_factory=list)
    version: int = Field(1, alias="repodata_version")

    def update(
        self,
        packages: Optional[PackageDict] = None,
        conda_packages: Optional[PackageDict] = None,
        removed: Optional[List[str]] = None,
    ):
        if packages is not None:
            _update_package_dict(packages, self.packages)

        if conda_packages is not None:
            _update_package_dict(conda_packages, self.conda_packages)

        if removed is not None:
            self.removed.extend(removed)


class PatchInstructions(BaseModel):
    conda_packages: PackageDict = Field(alias="conda.packages", default_factory=dict)
    packages: PackageDict = Field(default_factory=dict)
    remove: List[str] = Field(default_factory=list)
    revoke: List[str] = Field(default_factory=list)
    version: int = Field(1, alias="patch_instructions_version")

    def update(
        self,
        packages: Optional[PackageDict] = None,
        conda_packages: Optional[PackageDict] = None,
        remove: Optional[List[str]] = None,
        revoke: Optional[List[str]] = None,
    ):
        if packages is not None:
            _update_package_dict(packages, self.packages)

        if conda_packages is not None:
            _update_package_dict(conda_packages, self.conda_packages)

        if remove is not None:
            self.remove.extend(remove)

        if revoke is not None:
            self.revoke.extend(revoke)


def _update_package_dict(source: PackageDict, destination: PackageDict) -> None:
    for key, value in source.items():
        if key in destination:
            destination[key].update(value)
