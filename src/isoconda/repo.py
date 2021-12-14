import json

from pathlib import Path
import pathlib
from typing import Any, Dict, Iterable, Iterator
from urllib.parse import urljoin, urlparse

import requests

from conda.exports import PackageRecord


def fetch_records(channel: str) -> Iterator[PackageRecord]:
    path = pathlib.Path(channel)
    if path.exists():
        yield from fetch_local_records(path)
        return
    yield from fetch_online_records(channel)


def fetch_local_records(channel: Path) -> Iterator[PackageRecord]:
    """Fetches package records from a local anaconda repository.

    Args:
        channel: Location of the local anaconda repository.

    Yields:
        Package records objects.
    """
    repodata = channel / "repodata.json"
    with repodata.open("rt") as file:
        data = json.load(file)
    yield from parse_repodata(data)


def fetch_online_records(url: str) -> Iterator[PackageRecord]:
    """Fetches package records from an online anaconda channel.

    Args:
        url: URL of the online anaconda repository.

    Yields:
        Package records objects.
    """
    if url[-1] != "/":
        url += "/"
    repodata = urljoin(url, "repodata.json")
    data = requests.get(repodata).json()
    yield from parse_repodata(data)


def get_repodata_urls(channel_url: str, platforms: Iterable[str]) -> Iterator[str]:
    for platform in platforms:
        yield urljoin(channel_url, platform)


def parse_repodata(data: Dict[Any, Any]) -> Iterator[PackageRecord]:
    """Parses anaconda repository data into package records.

    Args:
        data: Anaconda repository data (normally from a repodata.json).

    Yields:
        Package record objects.
    """
    packages = data.get("packages", {})
    for file_name, package_data in packages.items():
        yield PackageRecord(fn=file_name, **package_data)
