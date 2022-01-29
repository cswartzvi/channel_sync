"""High-level api functions for conda-local."""

from typing import Dict, Iterable, Iterator, Tuple

from conda_local.dep_finder import DependencyFinder
from conda_local.external import ChannelData, PackageRecord, no_channel_hash
from conda_local.utils import groupby


def create_repodata(records: Iterable[PackageRecord]) -> Dict:
    subdir_groups = groupby(records, lambda pkg: pkg.subdir)


def diff_records(
    source: str, target: str, platforms: Iterable[str], specs: Iterable[str]
) -> Tuple[Iterable[PackageRecord], Iterable[PackageRecord]]:
    source_records = query_records(source, platforms, specs)
    target_records = query_records(target, platforms, specs)
    target_group = groupby(target_records, no_channel_hash)


def query_records(
    channel: str, platforms: Iterable[str], specs: Iterable[str]
) -> Iterable[PackageRecord]:
    finder = DependencyFinder(channel, platforms)
    yield from finder.search(specs)


def read_records(channel: str, platforms: Iterable[str]) -> Iterator[PackageRecord]:
    channel_data = ChannelData(channel, platforms)
    yield from channel_data.iter_records()
