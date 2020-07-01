import json
import pathlib
from typing import Iterable, Iterator, Union

import requests
from tqdm import tqdm

from isoconda.models import PackageRecord, RepoData

BLOCK_SIZE = 1024


def download_package(channel: str, package: PackageRecord, destination: pathlib.Path,
                     session: requests.Session):
    url = _urljoin(channel, package.subdir, package.filename)
    destination.mkdir(parents=True, exist_ok=True)
    filepath = destination / package.filename
    with session.get(url, stream=True) as response:
        with open(filepath, 'wb') as download:
            for data in response.iter_content(BLOCK_SIZE):
                download.write(data)

    # TODO: Verify packages with sha


def download_packages(channel: str, packages: Iterable[PackageRecord],
                      destination: Union[str, pathlib.Path]):
    destination = pathlib.Path(destination)
    with requests.Session() as session:
        for package in tqdm(list(packages), ascii=True, desc=channel):
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
    for repo in repos:
        yield _apply_filters(repo, include, exclude, versions)


def _apply_filters(repo: RepoData, include: Iterable[str], exclude: Iterable[str],
                   versions: Iterable[float]) -> RepoData:
    if include:
        repo = repo.filter_mismatches(include)
    if exclude:
        repo = repo.filter_matches(exclude)
    if versions:
        repo = repo.filter_python(versions)
    return repo


def _urljoin(*parts):
    """Concatenate url parts."""
    return '/'.join([part.strip('/') for part in parts])
