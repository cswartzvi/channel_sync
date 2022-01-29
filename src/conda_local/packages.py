"""Functionality for downloading anaconda packages."""

import hashlib
import shutil
from pathlib import Path
from typing import Iterable

from conda.models.records import PackageRecord
from requests import Session

BLOCK_SIZE = 65536  # 64 KiB


class DirectoryExists(Exception):
    pass


class InvalidChecksum(Exception):
    pass


def fetch_packages():
    pass


def download_packages(
    records: Iterable[PackageRecord],
    destination: Path,
    progress: bool = True,
    insecure: bool = False,
) -> None:
    """Downloads a packages to a given destination folder.

    Args:
        packages: The package records to be downloaded.
        destination: Folder where package record will be downloaded.

    Raises:
        ValueError: Package sha256 code cannot be verified.
    """

    with Session() as session:
        for record in records:
            _download_package(record, destination, session, insecure)

    noarch_subdir = destination / "noarch"
    noarch_repodata = noarch_subdir / "repodata.json"
    noarch_subdir.mkdir(parents=True, exist_ok=True)


def _download_package(
    record: PackageRecord, destination: Path, session: Session, insecure: bool = False
) -> Path:
    """Downloads a package to a given destination folder.

    Args:
        package: A package record to be downloaded.
        destination: Folder where package record will be downloaded.
        session: Current browser session.

    Raises:
        DirectoryExists: Package sha256 code cannot be verified.
    """
    filepath = destination / str(record.subdir) / str(record.fn)

    if filepath.exists():
        if filepath.is_dir():
            raise DirectoryExists(str(filepath.resolve()))
        file_bytes = filepath.read_bytes()
        if record.sha256 == hashlib.sha256(file_bytes).hexdigest():
            return filepath
        filepath.unlink()  # TODO: Is this necessary? Or can we just overrite?

    filepath.parent.mkdir(parents=True, exist_ok=True)
    sha256_hash = hashlib.sha256()

    with session.get(record.url, stream=True) as response:
        response.raise_for_status()
        with open(filepath, "wb") as file:
            # for data in response.iter_content(BLOCK_SIZE):
            #     file.write(data)
            sha256_hash.update(response.raw)
            shutil.copyfileobj(response.raw, file)

    # Verify the hash of the package
    readable_hash = sha256_hash.hexdigest()
    if record.sha256 != readable_hash:
        # TODO: log this mismatch
        if not insecure:
            filepath.unlink()  # delete package
            raise InvalidChecksum(
                f"url={record.url}, expected={record.sha256}, found={readable_hash}"
            )
    return filepath
