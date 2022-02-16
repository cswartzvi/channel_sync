"""Adapters for the `conda` and `conda_build` public (and not so public) APIs."""

import hashlib
import logging
from pathlib import Path
from typing import Iterable, Iterator, List

# NOTE: import marked as 'noqa' are currently pass throughs.
from conda.api import SubdirData
from conda.common.io import Spinner  # noqa
from conda.exceptions import UnavailableInvalidChannel  # noqa
from conda.exports import PackageRecord as _PackageRecord
from conda.exports import _download
from conda_build.api import update_index  # noqa

LOGGER = logging.Logger(__name__)


class PackageRecord:
    """A wrapper around `conda.models.records.PackageRecord`.

    The main purpose of this wrapper is to provide a package record
    whose hash and equality methods DO NOT depend on the package's
    channel. All other functionality is delgated to the internal
    conda.PackageRecord.
    """

    def __init__(self, record: _PackageRecord) -> None:
        self._internal = record
        self._pkey = (
            self._internal.subdir,
            self._internal.name,
            self._internal.version,
            self._internal.build_number,
            self._internal.build,
        )
        self._hash = hash(self._pkey)

    @property
    def build(self) -> str:
        return self._internal.build

    @property
    def build_number(self) -> int:
        return self._internal.build_number

    @property
    def channel(self) -> str:
        return self._internal.channel

    @property
    def depends(self) -> List[str]:
        return self._internal.depends

    @property
    def fn(self) -> str:
        return self._internal.fn

    @property
    def local_path(self) -> Path:
        """Returns the relative path of this package in a local anaconda channel."""
        return Path(self.subdir) / self.fn

    @property
    def name(self) -> str:
        return self._internal.name

    @property
    def sha256(self) -> str:
        return self._internal.sha256

    @property
    def size(self) -> str:
        return self._internal.size

    @property
    def subdir(self) -> str:
        return self._internal.subdir

    @property
    def version(self) -> str:
        return self._internal.version

    @property
    def url(self) -> str:
        return self._internal.url

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, self.__class__):
            return False
        return self._pkey == other._pkey

    def __hash__(self) -> int:
        return self._hash

    def __repr__(self) -> str:
        return repr(self._internal)

    def __str__(self) -> str:
        return str(self._internal)


class ChannelData:
    """High-level management and usage of an anaconda channel.

    Args:
        channel: The target anaconda channel url or identifier, e.g.:
            * "https://repo.anaconda.com/pkgs/main/linux-64"
            * "conda-forge/linux-64"
            * "file:///path/to/local/channel"
        subdirs: The platform sub-directories within the anaconda channel.
    """

    def __init__(self, channels: Iterable[str], subdirs: Iterable[str]) -> None:
        self._channels = channels
        self._subdirs = subdirs
        self._subdir_data: List[SubdirData] = []  # cache (see self.reload)

    def iter_records(self) -> Iterator[PackageRecord]:
        """Yields all package records contained in the anaconda channel."""
        yield from self.query("*")

    def query(self, specs: Iterable[str]) -> Iterator[PackageRecord]:
        """Run a package record query against the anaconda channel.

        Args:
            specs: The package match specifications used within the query. Read more:
                https://docs.conda.io/projects/conda/en/latest/user-guide/concepts/pkg-specs.html#package-match-specifications  # noqa

        Returns:
            A set of all packages satisfying the package match specification.
        """
        yield from (
            PackageRecord(result)
            for spec in specs
            for result in SubdirData.query_all(
                spec, channels=self._channels, subdirs=self._subdirs
            )
        )

    def reload(self) -> None:
        """Reload cached repodata.json files for subdirs."""
        if not self._subdir_data:
            for channel in self._channels:
                for subdir in self._subdirs:
                    if not channel.endswith("/"):
                        channel += "/"
                    subdir_data = SubdirData(channel + subdir)
                    self._subdir_data.append(subdir_data)

        for subdir_data in self._subdir_data:
            subdir_data.reload()


def download_package(
    record: PackageRecord, destination: Path, verify: bool = True
) -> None:
    """Downloads the package specified by a package record.

    Args:
        record: The package record for the package that is to be downloaded.
        destination: The directory where the package will be downloaded.
            Additional subdirs will be created within the destination directory.
        verify: Flag indicating if packages should be verified.
    """
    sha256_hash = record.sha256 if verify else None
    size = record.size if verify else None
    path = destination / record.local_path
    if path.exists():
        if verify:
            if verify_file(path, record):
                return  # skip file
            LOGGER.warn(
                "Existing file failed verification, will be overwritten: %s",
                str(path.resolve()),
            )
        else:
            return  # skip file
    path.parent.mkdir(parents=True, exist_ok=True)
    _download(record.url, path, sha256=sha256_hash, size=size)


def verify_file(path: Path, record: PackageRecord) -> bool:
    """Verifies that a file matches the sha256 and size of specified package record.

    Args:
        path: The file path that will be verified.
        record: The package record used to perfrom the verification.
    """
    file_size = path.stat().st_size
    file_bytes = path.read_bytes()
    file_hash = hashlib.sha256(file_bytes).hexdigest()
    return record.sha256 == file_hash and record.size == file_size
