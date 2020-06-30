from __future__ import annotations
from typing import Iterable, Iterator, List

import requests

from isoconda.channel import ChannelData
from isoconda.repo import RepoData
from isoconda.utils import urljoin

class Source:

    def __init__(self, location: str, subdir: str):
        self._location = location
        self._subdir = subdir
        self._repos: RepoData = self._read_repo(location, subdir)

    @classmethod
    def _read_repo(cls, location: str, subdir: str) -> RepoData:
        url = urljoin(location, subdir, 'repodata.json')
        data = requests.get(url).json()
        return RepoData.from_data(data)