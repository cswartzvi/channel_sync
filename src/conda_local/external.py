"""External interface for the `conda` and `conda_build` public (and not so
public) APIs."""

import hashlib
import json
import logging
import tarfile
import tempfile
import urllib.parse
from pathlib import Path
from typing import Iterable, Iterator, List, Optional, Sequence, Set, Tuple

import conda.api
import conda.base.context
import conda.exports
import conda.models.channel
import conda_build.api
import requests

# Passthrough imports
from conda.common.io import Spinner  # noqa
from conda.exceptions import UnavailableInvalidChannel  # noqa
from conda.exports import MatchSpec, PackageRecord

from conda_local.utils import Grouping, groupby

LOGGER = logging.Logger(__name__)
PATCH_INSTRUCTIONS = "patch_instructions.json"


def compare_records(
    left: Iterable[PackageRecord], right: Iterable[PackageRecord]
) -> Tuple[Set[PackageRecord], Set[PackageRecord]]:
    def no_channel_key(record):
        return (
            record.subdir,
            record.name,
            record.version,
            record.build,
            record.build_number,
        )

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
    conda.exports._download(record.url, path, sha256=sha256_hash, size=size)


def download_patch_instructions(
    channels: Iterable[str],
    destination: Path,
    subdir: str,
    packages_to_remove: Optional[Sequence[PackageRecord]] = None,
) -> None:

    base_url = conda.models.channel.all_channel_urls(channels, subdirs=[subdir])[0]
    url = urllib.parse.urljoin(base_url + "/", PATCH_INSTRUCTIONS)
    response = requests.get(url)
    response.raise_for_status()

    destination.mkdir(parents=True, exist_ok=True)
    instructions = destination / subdir / PATCH_INSTRUCTIONS
    instructions.parent.mkdir(parents=True, exist_ok=True)
    instructions.write_bytes(response.content)

    if packages_to_remove:
        with instructions.open("r+") as file:
            data = json.load(file)
            for package in packages_to_remove:
                data["remove"].append(package.fn)
            file.seek(0)
            json.dump(data, file)


def get_current_subdirs() -> List[str]:
    return list(conda.base.context.context.subdirs)


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


def query_channels(
    channels: Iterable[str], subdirs: Iterable[str], specs: Iterable[str],
) -> Iterator[PackageRecord]:
    """Runs a package record query against the specified anaconda channels.

    Args:
        channels: An iterable of anaconda channel urls or identifies, e.g.:
            * "https://repo.anaconda.com/pkgs/main"
            * "conda-forge"
            * "file:///path/to/local/channel"
        specs: The package match specifications used within the query. Read more:
            https://docs.conda.io/projects/conda/en/latest/user-guide/concepts/pkg-specs.html#package-match-specifications  # noqa
        subdirs: The platform sub-directories within the anaconda channel. If
            None defaults to the standard subdirs for the current platform.

    Yields:
        Package records resulting from the package record query.
    """
    yield from (
        result
        for spec in specs
        for result in conda.api.SubdirData.query_all(
            spec, channels=channels, subdirs=subdirs
        )
    )


def update_index(
    target: Path, subdirs: Iterable[str], progress: bool = False,
):
    patches = [Path(subdir) / PATCH_INSTRUCTIONS for subdir in subdirs]

    with tempfile.TemporaryDirectory() as tmpdir:
        patch_generator = None
        if patches:
            tmppath = Path(tmpdir)
            tarball = tmppath / "patch_generator.tar.bz2"
            with tarfile.open(tarball, "w:bz2") as tar:
                for patch in patches:
                    tar.add(target / patch, arcname=patch)
            patch_generator = str(tarball.resolve())  # must be string (or None)

        conda_build.api.update_index(
            target, patch_generator=patch_generator, progress=progress
        )


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
