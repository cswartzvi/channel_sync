from __future__ import annotations

import hashlib
import json
import shutil
import tarfile
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Tuple, Union

import conda.api
import conda.exports
import conda_build.api
import fsspec
from pydantic import BaseModel
from pydantic import Field

from conda_replicate import CondaReplicateException
from conda_replicate.adapters.package import CondaPackage
from conda_replicate.adapters.subdir import get_known_subdirs

_PATCH_GENERATOR_FILE = "patch_generator.tar.bz2"
_INSTRUCTIONS_FILE = "patch_instructions.json"
_REPODATA_FILE = "repodata.json"

PackageDict = Dict[str, Dict[str, Any]]


class CondaChannel:
    """Adapter for the external `conda` Channel class.

    Args:
        source: External `conda` object.
    """

    def __init__(self, source: str) -> None:
        source = source.replace("\\", "/")
        self._internal = conda.exports.Channel(source)
        if source.startswith("//"):
            # Representation of UNC in fsspec and conda is inconsistent
            self._filesystem = CondaFilesystem(source)
        else:
            self._filesystem = CondaFilesystem(self._internal.base_url)

    @property
    def name(self) -> str:
        """Returns the canonical name of the anaconda channel."""
        return self._internal.canonical_name

    @property
    def url(self) -> str:
        """Returns the complete URL of the anaconda channel."""
        return self._filesystem.url

    @property
    def is_queryable(self) -> bool:
        """Determines if the conda channel is currently queryable.

        Channels are queryable if and only if their index has been created.
        """
        return self._filesystem.contains_file("noarch", _REPODATA_FILE)

    def find_subdirs(self) -> Tuple[str, ...]:
        """Returns all platform sub-directories within the underlying filesystem."""
        subdirs = tuple(
            subdir
            for subdir in get_known_subdirs()
            if self._filesystem.contains_directory(subdir)
        )
        return subdirs

    def iter_packages(self, subdirs: Iterable[str]) -> Iterator[CondaPackage]:
        """Yields all conda packages within the specified platform sub-directories.

        Args:
            subdirs: An iterable of platform sub-directories.
        """
        return self.query_packages("*", subdirs=subdirs)

    def query_packages(
        self, spec: str, subdirs: Iterable[str]
    ) -> Iterator[CondaPackage]:
        """Queries conda packages within the specified platform sub-directories.

        Args:
            spec: Anaconda match specification string (query syntax used in
                `conda search`)
            subdirs: An iterable of platform sub-directories.
        """
        query = conda.api.SubdirData.query_all(
            spec, channels=[self._internal], subdirs=subdirs
        )
        packages = (CondaPackage(package) for package in query)
        yield from packages

    def setup(self) -> None:
        """Constructs the minimal required filesystem structure."""
        if not self._filesystem.contains_file("noarch", _REPODATA_FILE):
            self._filesystem.write_file("noarch", _REPODATA_FILE, b"")

    def add_package(self, package: CondaPackage) -> None:
        """Adds a conda package to the underlying filesystem.

        Added packages are not queryable until the index of the channel has
        been updated.

        Args:
            package: A conda package object to add.

        Raises:
            BadPackageDownload: Downloaded file does not match either the advertised
            size of sha256 string.
        """
        if self.contains_package(package):
            contents = self._filesystem.read_file(package.subdir, package.fn)
            if hashlib.sha256(contents).hexdigest() == package.sha256:
                return

        with fsspec.open(package.url, "rb") as fp:
            contents = fp.read()

        if len(contents) != package.size:
            raise BadPackageDownload(f"{package.fn} has incorrect size")
        if package.sha256 != hashlib.sha256(contents).hexdigest():
            raise BadPackageDownload(f"{package.fn} has incorrect sha256")

        self._filesystem.write_file(package.subdir, package.fn, contents)

    def remove_package(self, package: CondaPackage) -> None:
        """Remove a conda package from the underlying filesystem.

        Removed packages are still queryable until the index of the channel
        has been updated.

        Args:
            package: A conda package object to remove.
        """
        self._filesystem.remove_file(package.subdir, package.fn)

    def contains_package(self, package: CondaPackage) -> bool:
        """Determines if a conda package exists in the underlying filesystem.

        Args:
            package: A conda package object to check.
        """
        return self._filesystem.contains_file(package.subdir, package.fn)

    def read_instructions(self, subdir: str) -> PatchInstructions:
        """Reads platform specific patch instructions from the underlying filesystem.

        Args:
            subdir: Platform sub-directory of the patch instructions.

        Returns:
            A validated PatchInstructions object.
        """
        contents = self._filesystem.read_file(subdir, _INSTRUCTIONS_FILE, b"{}")
        instructions = PatchInstructions.parse_raw(contents)
        return instructions

    def write_instructions(self, subdir: str, instructions: PatchInstructions) -> None:
        """Writes platform specific patch instructions to the underlying filesystem.

        Args:
            subdir: Platform sub-directory of the patch instructions.
            instructions: A PatchInstructions object to write.
        """
        contents = json.dumps(instructions.dict(by_alias=True), indent=2)
        self._filesystem.write_file(
            subdir, _INSTRUCTIONS_FILE, contents.encode("utf-8")
        )

    def read_repodata(self, subdir: str) -> RepoData:
        """Reads platform specific repodata from the underlying filesystem.

        Args:
            subdir: Platform sub-directory of the repodata.

        Returns:
            A validated RepoData object.
        """
        contents = self._filesystem.read_file(subdir, _REPODATA_FILE, b"{}")
        repodata = RepoData.parse_raw(contents)
        return repodata

    def write_repodata(self, subdir: str, repodata: RepoData) -> None:
        """Writes platform specific repodata to the underlying filesystem.

        Args:
            subdir: Platform sub-directory of the patch instructions.
            instructions: A RepoData object to write.
        """
        contents = json.dumps(repodata.dict(by_alias=True), indent=2)
        self._filesystem.write_file(subdir, _REPODATA_FILE, contents.encode("utf-8"))


class LocalCondaChannel(CondaChannel):
    """An extension of the anaconda channel for local filesystems.

    Note: the functionality in this class is currently only possible with a local
    filesystem.
    """

    # TODO: Merge this class with CondaChannel when/if the index functionality is
    # re-implemented to use fsspec.

    def __init__(self, source: Union[str, Path]) -> None:
        self._path = Path(source).resolve()
        if not self._path.exists():
            self._path = self._path.absolute()
        super().__init__(str(self._path.resolve()))

    @property
    def path(self) -> Path:
        """Returns the complete URL of the anaconda channel."""
        return self._path

    def update_index(self) -> None:
        """Update the package index of the channel."""
        generator = self._path / _PATCH_GENERATOR_FILE
        conda_build.api.update_index(
            self._path, patch_generator=str(generator.resolve()), progress=True
        )
        self._purge_removed_packages()

    def merge(self, source: LocalCondaChannel) -> None:
        """Merge the underlying filesystems of the another channel."""
        shutil.copytree(source._path, self._path, dirs_exist_ok=True)

    def write_patch_generator(self) -> None:
        """Write a patch generator to the underlying filesystem.

        A patch generator is a tarball of patch instructions for all relevant
        platform sub-directories.
        """
        generator = self._path / _PATCH_GENERATOR_FILE
        generator.parent.mkdir(exist_ok=True, parents=True)
        with tarfile.open(generator, "w:bz2") as tar:
            for instructions in self._path.glob("**/" + _INSTRUCTIONS_FILE):
                tar.add(instructions, arcname=instructions.relative_to(self._path))

    def _purge_removed_packages(self) -> None:
        """Purge files marked for removal from underlying filesystem."""
        for subdir in self.find_subdirs():
            repodata = self.read_repodata(subdir)
            for filename in repodata.removed:
                self._filesystem.remove_file(subdir, filename)
            repodata.removed = []
            self.write_repodata(subdir, repodata)


class CondaFilesystem:
    """The underlying abstract filesystem of an anaconda channel.

    Anaconda channel filesystems are made up of top level sub-directories that are
    each associated with a specific platform. The bulk of data is stored directly
    within these sub-directories (with the exception of some metadata that is
    generated by conda itself).

    Args:
        url: URL (or local path) of the filesystem. Note that this URL is parsed
            by `fspec`, see their documentation for URL details.
    """

    def __init__(self, url: str) -> None:
        self._url = url
        self._mapper = fsspec.get_mapper(url)

    @property
    def url(self) -> str:
        """Returns the URL of the filesystem."""
        return self._url

    def read_file(
        self, subdir: str, filename: str, default: Optional[bytes] = None
    ) -> bytes:
        """Reads data from a file within the filesystem.

        Args:
            subdir: Platform sub-directory of the file.
            filename: Name of the file.
            default (optional): Fallback value for read failures. If None, read
                failures wil raise a `KeyError`.

        Returns:
            The binary contents of the file.
        """
        urlpath = self.urlpath(subdir, filename)
        if default is None:
            contents = self._mapper[urlpath]
        else:
            contents = self._mapper.get(urlpath, default)
        return contents

    def write_file(self, subdir: str, filename: str, contents: bytes) -> None:
        """Write data to a file within the filesystem.

        Args:
            subdir: Platform sub-directory of the file.
            filename: Name of the file.
            contents: Binary contents of the file.
        """
        urlpath = self.urlpath(subdir, filename)
        self._mapper[urlpath] = contents

    def remove_file(self, subdir: str, filename: str) -> None:
        """Remove a file from the filesystem.

        Args:
            subdir: Platform sub-directory of the file.
            filename: Name of the file.
        """
        urlpath = self.urlpath(subdir, filename)
        del self._mapper[urlpath]

    def contains_file(self, subdir: str, filename: str) -> bool:
        """Determine if a file exists within the filesystem.

        Args:
            subdir: Platform sub-directory of the file.
            filename: Name of the file.

        Returns:
            True if the file exists, False otherwise.
        """
        urlpath = self.urlpath(subdir, filename)
        return urlpath in self._mapper

    def contains_directory(self, directory: str) -> bool:
        """Determine if a directory exists within the filesystem.

        Args:
            filename: Name of the directory.

        Returns:
            True if the directory exists, False otherwise.
        """
        return self._mapper.fs.exists(self.urlpath(self.url, directory))

    def urlpath(self, *parts: str) -> str:
        """Returns a URL of an object within the filesystem relative the root."""
        return "/".join(parts)

    def __repr__(self):
        class_name = self.__class__.__name__
        return f"<{class_name}: url={self.url!r}>"


class BadPackageDownload(CondaReplicateException):
    """Downloaded package does not match advertised specifications."""

    pass


class RepoData(BaseModel):
    """Represents the data in a platform specific repodata.json file."""

    info: Dict[str, str] = Field(default_factory=dict)
    packages: PackageDict = Field(default_factory=dict)
    conda_packages: PackageDict = Field(alias="conda.packages", default_factory=dict)
    removed: List[str] = Field(default_factory=list)
    version: int = Field(1, alias="repodata_version")


class PatchInstructions(BaseModel):
    """Represents the data in a platform specific patch_instructions.json file."""

    conda_packages: PackageDict = Field(alias="conda.packages", default_factory=dict)
    packages: PackageDict = Field(default_factory=dict)
    remove: List[str] = Field(default_factory=list)
    revoke: List[str] = Field(default_factory=list)
    version: int = Field(1, alias="patch_instructions_version")
