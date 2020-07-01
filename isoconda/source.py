from __future__ import annotations
from typing import Iterable, List, Optional

import requests

from isoconda.models.channel import ChannelData
from isoconda.models.repo import RepoData


class Source:

    def __init__(self, location: str, channel: ChannelData, repos: Iterable[RepoData]):
        self._location = location
        self._channel = channel
        self._repos = list(repos)

    @classmethod
    def from_channel(cls, location: str, subdirs: Optional[Iterable[str]] = None) -> Source:

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
        return Source(location, channel, repos)


def urljoin(*parts):
    """Concatenate url parts."""
    return '/'.join([part.strip('/') for part in parts])
