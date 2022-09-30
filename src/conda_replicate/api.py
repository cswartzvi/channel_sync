from dataclasses import dataclass, field
import pathlib
from typing import List, Optional, Set

from rich.console import Console

from conda_replicate import CondaReplicateException
from conda_replicate.adapters.channel import CondaChannel
from conda_replicate.adapters.channel import LocalCondaChannel
from conda_replicate.adapters.package import CondaPackage
from conda_replicate.adapters.subdir import get_default_subdirs
from conda_replicate.display import Display
from conda_replicate.query import ExclusionFilter, LatestBuildFilter
from conda_replicate.query import InclusionFilter
from conda_replicate.query import LatestVersionFilter
from conda_replicate.query import PackageFilter
from conda_replicate.query import crate_package_query
from conda_replicate.resolve import resolve_packages
from conda_replicate._typing import (
    ChannelSource,
    Latest,
    LocalChannelSource,
    Specs,
    Subdirs,
)

LATEST = ["all", "version", "build"]


@dataclass
class QueryResults:
    added: Set[CondaPackage] = field(default_factory=set)
    removed: Set[CondaPackage] = field(default_factory=set)


def get_channel(source: ChannelSource) -> CondaChannel:
    if not isinstance(source, CondaChannel):
        if isinstance(source, pathlib.Path):
            source = str(source.resolve())
        source = CondaChannel(source)
    if not source.is_queryable:
        raise CondaReplicateException("Invalid channel")
    return source


def get_local_channel(source: LocalChannelSource) -> LocalCondaChannel:
    if not isinstance(source, LocalCondaChannel):
        path = pathlib.Path(source)
        path.mkdir(parents=True, exist_ok=True)
        source = LocalCondaChannel(source)
    source.setup()
    if not source.is_queryable:
        raise CondaReplicateException("Invalid channel")
    return source


def query(
    channel: ChannelSource,
    requirements: Specs,
    *,
    target: Optional[ChannelSource] = None,
    subdirs: Optional[Subdirs] = None,
    exclusions: Optional[Specs] = None,
    disposables: Optional[Specs] = None,
    latest: Optional[Latest] = None,
    latest_roots: bool = False,
    console: Optional[Console] = None,
) -> QueryResults:

    channel = get_channel(channel)
    subdirs = subdirs if subdirs else get_default_subdirs()
    console = console if console else Console(quiet=True)
    display = Display(console)

    filters: List[PackageFilter] = []
    if requirements:
        filters.append(InclusionFilter(requirements))

    if exclusions:
        filters.append(ExclusionFilter(exclusions))

    if latest in ["all", "version"]:
        if latest_roots:
            filters.append(LatestVersionFilter(requirements))
        else:
            filters.append(LatestVersionFilter())

    if latest in ["all", "build"]:
        if latest_roots:
            filters.append(LatestBuildFilter(requirements))
        else:
            filters.append(LatestBuildFilter())

    query = crate_package_query(channel, subdirs, *filters)
    resolver = resolve_packages(requirements, query)

    if disposables:
        filter_ = ExclusionFilter(disposables)
        resolver = filter_(resolver)

    with display.status("Search for packages"):
        packages = set(resolver)

    if target is not None:
        target = get_channel(target)
        target_packages = set(target.iter_packages(subdirs))
        packages = set(packages)
        results = QueryResults(
            added=packages.difference(target_packages),
            removed=target_packages.difference(packages),
        )
    else:
        results = QueryResults(added=packages)

    return results


def update(
    channel: ChannelSource,
    requirements: Specs,
    target: LocalChannelSource,
    *,
    subdirs: Optional[Subdirs] = None,
    exclusions: Optional[Specs] = None,
    disposables: Optional[Specs] = None,
    latest: Optional[Latest] = None,
    latest_roots: bool = False,
    console: Optional[Console] = None,
) -> None:

    target = get_local_channel(target)
    channel = get_channel(channel)
    subdirs = subdirs if subdirs else get_default_subdirs()

    console = console if console else Console(quiet=True)
    display = Display(console)

    results = query(
        channel,
        requirements,
        exclusions=exclusions,
        disposables=disposables,
        target=target,
        subdirs=subdirs,
        latest=latest,
        latest_roots=latest_roots,
        console=console,
    )

    for package in display.progress(results.added, "Downloading packages"):
        target.add_package(package)

    for package in display.progress(results.removed, "Removing packages"):
        target.remove_package(package)

    for subdir in display.progress(subdirs, "Updating patch instructions"):
        instructions = channel.read_instructions(subdir)
        target.write_instructions(subdir, instructions)

    with display.status("Creating patch generator"):
        target.write_patch_generator()

    with display.status_monkeypatch_conda_index("Updating channel index"):
        target.update_index()


def create_patch(
    destination: LocalChannelSource,
    channel: ChannelSource,
    requirements: Specs,
    *,
    target: Optional[ChannelSource] = None,
    subdirs: Optional[Subdirs] = None,
    exclusions: Optional[Specs] = None,
    disposables: Optional[Specs] = None,
    latest: Optional[Latest] = None,
    latest_roots: bool = False,
    console: Optional[Console] = None,
) -> None:

    destination = get_local_channel(destination)
    channel = get_channel(channel)
    subdirs = subdirs if subdirs else get_default_subdirs()

    console = console if console else Console(quiet=True)
    display = Display(console)

    results = query(
        channel,
        requirements,
        exclusions=exclusions,
        disposables=disposables,
        target=target,
        subdirs=subdirs,
        latest=latest,
        latest_roots=latest_roots,
        console=console,
    )

    for package in display.progress(results.added, "Downloading packages"):
        destination.add_package(package)

    for subdir in display.progress(subdirs, "Updating patch instructions"):
        instructions = channel.read_instructions(subdir)
        instructions.remove.extend(pkg.fn for pkg in results.removed)
        destination.write_instructions(subdir, instructions)

    with display.status("Creating patch generator"):
        destination.write_patch_generator()


def merge_patch(
    source: LocalChannelSource,
    destination: LocalChannelSource,
    *,
    console: Optional[Console] = None,
) -> None:
    source = get_local_channel(source)
    destination = get_local_channel(destination)
    console = console if console else Console(quiet=True)
    display = Display(console)

    destination.merge(source)

    with display.status_monkeypatch_conda_index("Updating channel index"):
        destination.update_index()


def index(channel: LocalChannelSource, *, console: Optional[Console] = None) -> None:
    channel = get_local_channel(channel)
    console = console if console else Console(quiet=True)
    display = Display(console)
    with display.status_monkeypatch_conda_index("Updating channel index"):
        channel.update_index()
