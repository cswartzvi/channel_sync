"""High-level functions for working with package records (vice actual packages)."""

from typing import Iterable, Tuple

import networkx as nx

from conda_sync.depends import DependencyScout
from conda_sync.external import ChannelData, PackageRecord


def diff_records(
    channel: str, platforms: Iterable[str], records: Iterable[PackageRecord]
) -> Tuple[Iterable[PackageRecord], Iterable[PackageRecord]]:
    pass


def query_records(
    channel: str, platforms: Iterable[str], specs: Iterable[str]
) -> Tuple[Iterable[PackageRecord], nx.DiGraph]:
    scout = DependencyScout(channel, platforms)
    records, graph = scout.search(specs)
    return records, graph


def read_records(channel: str, platforms: Iterable[str]) -> Iterable[PackageRecord]:
    channel_data = ChannelData(channel, platforms)
    return channel_data.iter_records()
