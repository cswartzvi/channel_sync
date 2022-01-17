import hashlib
from pathlib import Path

from conda.models.records import PackageRecord
from requests import Session

BLOCK_SIZE = 1024


def download_package(package: PackageRecord, destination: Path, session: Session):
    """Downloads a package to a given destination folder.

    Args:
        package: A package record to be downloaded.
        destination: Folder where package record will be downloaded.
        session: Current browser session.

    Raises:
        ValueError: Package sha256 code cannot be verified.
    """
    filepath = destination / package.filename

    with session.get(package.url, stream=True) as response:
        with open(filepath, "wb") as download:
            for data in response.iter_content(BLOCK_SIZE):
                download.write(data)


def check_sha256(file: Path, expected: str) -> bool:
    """Checks the sha256 hash of a file

    Args:
        file: The file that will be have it's hash file checked.
        expected: Expected hash value.

    Returns:
        True if sha256 matches the file.
    """
    sha256_hash = hashlib.sha256()
    with file.open("rb") as f:
        for byte_block in iter(lambda: f.read(BLOCK_SIZE * 4), b""):
            sha256_hash.update(byte_block)
        return expected == sha256_hash.hexdigest()
