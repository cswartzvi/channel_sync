from __future__ import annotations
import pathlib
from typing import Iterable, List, Optional

import json
import requests

from isoconda.models.channel import ChannelData
from isoconda.models.repo import RepoData


class Cloud:

    def __init__(self, location: str, channel: ChannelData, repos: Iterable[RepoData]):
        self._location = location
        self._channel = channel
        self._repos = list(repos)

    @classmethod
    def from_source(cls, location: str, subdirs: Optional[Iterable[str]] = None) -> Cloud:

        with requests.Session() as session:
            data = session.get(urljoin(location, 'channeldata.json')).json()
            channel = ChannelData.from_data(data)
            if subdirs is None:
                subdirs = channel.subdirs

            repos: List[RepoData] = list()
            for subdir in subdirs:
                data = session.get(urljoin(location, subdir, 'repodata.json')).json()
                repos.append(RepoData.from_data(data))

            channel = channel.rescale(repos)
        return Cloud(location, channel, repos)

    def difference(self, local: Local) -> Cloud:
        pass


class Local:

    def __init__(self, location: str, channel: ChannelData, repos: Iterable[RepoData]):
        self._location = location
        self._channel = channel
        self._repos = list(repos)

    def from_source(cls, location: str, subdirs: Optional[Iterable[str]] = None) -> Cloud:

        path = pathlib.Path(location)
        data = json.load((path / 'channeldata.json').open('rt'))
        channel = ChannelData.from_data(data)
        if subdirs is None:
            subdirs = channel.subdirs

        repos: List[RepoData] = list()
        for subdir in subdirs:
            data = json.load((path / subdir / 'repodata.json').open('rt'))
            repos.append(RepoData.from_data(data))

        channel = channel.rescale(repos)
        return Cloud(location, channel, repos)


def urljoin(*parts):
    """Concatenate url parts."""
    return '/'.join([part.strip('/') for part in parts])
