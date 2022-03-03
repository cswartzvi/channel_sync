"""External interface for the `conda` and `conda_build` public (and not so
public) APIs."""

import hashlib
import logging
from pathlib import Path
from typing import Iterable, Iterator, Set, Tuple

# NOTE: pass throughs to the api should be marked as 'noqa'
from conda.api import SubdirData
from conda.common.io import Spinner  # noqa
from conda.exceptions import UnavailableInvalidChannel  # noqa
from conda.exports import MatchSpec  # noqa
from conda.exports import PackageRecord, _download  # noqa
from conda_build.api import update_index  # noqa

from conda_local.utils import Grouping, groupby

LOGGER = logging.Logger(__name__)


def compare_records(
    left: Iterable[PackageRecord], right: Iterable[PackageRecord]
) -> Tuple[Set[PackageRecord], Set[PackageRecord]]:
    left_group = groupby(left, no_channel_key)
    right_group = groupby(right, no_channel_key)
    only_in_left = {
        record
        for key in left_group.keys() - right_group.keys()
        for record in left_group[key]
    }
    only_in_right = {
        record
        for key in right_group.keys() - left_group.keys()
        for record in right_group[key]
    }
    return only_in_left, only_in_right


def create_spec_lookup(specs: Iterable[str]) -> Grouping[str, MatchSpec]:
    return groupby([MatchSpec(spec) for spec in specs], lambda spec: spec.name)


def download_package(
    record: PackageRecord, destination: Path, verify: bool = True
) -> None:
    """Downloads the package associated with a package record.

    Args:
        record: The package record for the package that is to be downloaded.
        destination: The directory where the package will be downloaded.
            Additional subdirs will be created within the destination directory.
        verify: Flag indicating if packages should be verified.
    """
    sha256_hash = record.sha256 if verify else None
    size = record.size if verify else None
    path = destination / record.subdir / record.fn
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


def iter_channels(
    channels: Iterable[str], subdirs: Iterable[str]
) -> Iterator[PackageRecord]:
    """Yields all package records in a channels / subdirs matrix.

    Args:
        channels: An iterable of anaconda channel urls or identifies, e.g.:
            * "https://repo.anaconda.com/pkgs/main/linux-64"
            * "conda-forge/linux-64"
            * "file:///path/to/local/channel"
        subdirs: The platform sub-directories within the anaconda channel.
    """
    yield from query_channels(channels, subdirs, ["*"])


def no_channel_key(record: PackageRecord) -> Tuple:
    return (
        record.subdir,
        record.name,
        record.version,
        record.build,
        record.build_number,
    )


def query_channels(
    channels: Iterable[str], subdirs: Iterable[str], specs: Iterable[str]
) -> Iterator[PackageRecord]:
    """Runs a package record query against the specified anaconda channels.

    Args:
        channels: An iterable of anaconda channel urls or identifies, e.g.:
            * "https://repo.anaconda.com/pkgs/main"
            * "conda-forge"
            * "file:///path/to/local/channel"
        subdirs: The platform sub-directories within the anaconda channel.
        specs: The package match specifications used within the query. Read more:
            https://docs.conda.io/projects/conda/en/latest/user-guide/concepts/pkg-specs.html#package-match-specifications  # noqa

    Yields:
        Package records resulting from the package record query.
    """
    yield from (
        result
        for spec in specs
        for result in SubdirData.query_all(spec, channels=channels, subdirs=subdirs)
    )


def reload_channels(
    channels: Iterable[str], subdirs: Iterable[str], specs: Iterable[str]
) -> None:
    """Reload cached repodata.json files for subdirs."""
    for channel in channels:
        for subdir in subdirs:
            if not channel.endswith("/"):
                channel += "/"
            SubdirData(channel + subdir).reload()


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
