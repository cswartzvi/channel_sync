from __future__ import annotations
import hashlib

import json
from operator import sub
from typing import Dict, Iterable, Iterator, Optional, Tuple

import fsspec
from conda.api import SubdirData as _SubdirData
from conda.exports import Channel as _Channel

from conda_local.group import groupby
from conda_local.models import PATCH_INSTRUCTIONS_FILE
from conda_local.models import REPODATA_FILE
from conda_local.models import get_known_subdirs
from conda_local.models.package import CondaPackage


class CondaChannelStorage:
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
            data = self._read_file(package.subdir, package.fn)
            if hashlib.sha256(data).hexdigest() == package.sha256:
                return

        data = response.content

        if len(data) != package.size:
            raise BadPackageDownload(f"{package.fn} has incorrect size")
        if package.sha256 != hashlib.sha256(data).hexdigest():
            raise BadPackageDownload(f"{package.fn} has incorrect sha256")

        path.parent.mkdir(exist_ok=True, parents=True)
        with path.open("wb") as file:
            file.write(data)

    def remove_package(self, package: CondaPackage) -> None:
        pass

    def contains_package(self, package: CondaPackage) -> bool:
        return self._contains_file(package.subdir, package.fn)

    def read_patch_instructions(self, subdir: str) -> Dict:
        contents = self._read_file(subdir, PATCH_INSTRUCTIONS_FILE, b"{}")
        instructions = json.loads(contents)
        return instructions

    def write_instructions(self, subdir: str, instructions: Dict) -> None:
        contents = json.dumps(instructions).encode("utf-8")
        self._write_file(subdir, PATCH_INSTRUCTIONS_FILE, contents)

    def read_repodata(self, subdir: str) -> Dict:
        contents = self._read_file(subdir, REPODATA_FILE, b"{}")
        repodata = json.loads(contents)
        return repodata

    def write_repodata(self, subdir: str, repodata: Dict) -> None:
        contents = json.dumps(repodata).encode("utf-8")
        self._write_file(subdir, REPODATA_FILE, contents)

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


class CondaChannel(CondaChannelStorage):
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

        results = tuple(CondaPackage(package) for package in packages)
        return results

    def update_index(self) -> None:
        pass

    def _purge_packages(self) -> None:
        pass

    def __repr__(self):
        class_name = self.__class__.__name__
        return f"<{class_name}: url={self.url!r}>"


class BadPackageDownload(CondaLocalException):
    pass
