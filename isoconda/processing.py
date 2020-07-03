import hashlib
import json
import pathlib
from typing import Iterable, Iterator, Union

import requests
import tqdm

from isoconda.errors import InvalidPackage
from isoconda.models import PackageRecord, RepoData

BLOCK_SIZE = 1024


def download_package(channel: str, package: PackageRecord, destination: pathlib.Path,
                     session: requests.Session):
    """Downloads a package to a given destination folder.

    Args:
        channel: Anaconda channel URL.
        package: Record of package to be downloaded.
        destination: Folder where package will be downloaded.
        session: Current browser session.

    Raises:
        InvalidPackage: Package sha256 code cannot be verified.
    """
    url = _urljoin(channel, package.subdir, package.filename)
    destination.mkdir(parents=True, exist_ok=True)
    filepath = destination / package.filename

    # We should ignore files that exist and have a valid hash code, we should
    # overwrite files with an invlaid hashcode.
    if filepath.exists():
        if package.sha256 == sha256(filepath):
            return

    with session.get(url, stream=True) as response:
        with open(filepath, 'wb') as download:
            for data in response.iter_content(BLOCK_SIZE):
                download.write(data)

    if package.sha256 != sha256(filepath):
        raise InvalidPackage(f"Failed to match sha256 for:{package.filename}")


def download_packages(channel: str, packages: Iterable[PackageRecord],
                      destination: Union[str, pathlib.Path]):
    """Downloads an iterable of packages to a given destination folder.

    Args:
        channel: Anaconda channel URL.
        packages: An iterable of records for packages to be downloaded.
        destination (Union[str, pathlib.Path]): Folder where packages will be downloaded.
    """
    destination = pathlib.Path(destination)
    subdir = destination.name
    desc = f"{subdir}:"
    bar_format = '{desc:<12}{percentage:3.0f}%|{bar:75}{r_bar}'
    with requests.Session() as session:
        for package in tqdm.tqdm(list(packages), ascii=True, bar_format=bar_format, desc=desc):
            download_package(channel, package, destination, session)


def fetch_local_repos(channel: str, subdirs: Iterable[str]) -> Iterator[RepoData]:
    """Yields ``RepoData`` object from a local Anaconda channel

    Args:
        channel: Path of the local Anaconda channel.
        subdirs: Iterable of platfrom sub-directories.
    """
    channel_path = pathlib.Path(channel)
    for subdir in subdirs:
        path = channel_path / subdir / 'repodata.json'
        data = json.load(path.open('rt'))
        yield RepoData.from_data(data)


def fetch_online_repos(channel: str, subdirs: Iterable[str]) -> Iterator[RepoData]:
    """Yields ``RepoData`` object from a online Anaconda channel

    Args:
        channel: Base URL of the online Anaconda channel.
        subdirs: Iterable of platfrom sub-directories.
    """
    with requests.Session() as session:
        for subdir in subdirs:
            url = _urljoin(channel, subdir, 'repodata.json')
            data = session.get(url).json()
            yield RepoData.from_data(data)


def filter_repos(repos: Iterable[RepoData], include: Iterable[str], exclude: Iterable[str],
                 versions: Iterable[float]) -> Iterator[RepoData]:
    """Applies filters to an iterable of Anaconda repositories."""
    for repo in repos:
        yield _apply_filters(repo, include, exclude, versions)


def _apply_filters(repo: RepoData, include: Iterable[str], exclude: Iterable[str],
                   versions: Iterable[float]) -> RepoData:
    """Applies filters to a single Anaconda repository."""
    if include:
        repo = repo.filter_mismatches(include)
    if exclude:
        repo = repo.filter_matches(exclude)
    if versions:
        repo = repo.filter_python(versions)
    return repo


def _md5(file: pathlib.Path) -> str:
    """Calculates the MD5 hash code of a file for integrity."""
    hash_md5 = hashlib.md5()
    with file.open("rb") as f:
        # Read and update hash string value in blocks of 4K
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def sha256(file: pathlib.Path) -> str:
    """Calculates the MD5 hash code of a file for integrity and security."""
    sha256_hash = hashlib.sha256()
    with file.open("rb") as f:
        # Read and update hash string value in blocks of 4K
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()


def _urljoin(*parts):
    """Concatenate url parts."""
    return '/'.join([part.strip('/') for part in parts])
