import datetime
import os
import pathlib
from typing import Dict, Iterable, List, Optional, Set, Tuple

from rich.console import Console

from conda_replicate import CondaReplicateException
from conda_replicate._typing import Specs, Subdir, Subdirs, StringOrPath
from conda_replicate.adapters.channel import CondaChannel
from conda_replicate.adapters.channel import LocalCondaChannel
from conda_replicate.adapters.channel import PatchInstructions
from conda_replicate.adapters.package import CondaPackage
from conda_replicate.adapters.subdir import get_default_subdirs
from conda_replicate.display import Display
from conda_replicate.query import ExclusionFilter
from conda_replicate.query import InclusionFilter
from conda_replicate.query import LatestVersionFilter
from conda_replicate.query import PackageFilter
from conda_replicate.query import crate_package_query
from conda_replicate.resolve import resolve_packages


def get_channel(url: str) -> CondaChannel:
    channel = CondaChannel(url)
    if not channel.is_queryable:
        raise CondaReplicateException("Invalid channel")
    return channel


def get_local_channel(path: StringOrPath, setup: bool = False) -> LocalCondaChannel:
    path = pathlib.Path(path)
    if setup:
        path.mkdir(parents=True, exist_ok=True)
    channel = LocalCondaChannel(path)
    if not channel.is_queryable:
        raise CondaReplicateException("Invalid channel")
    return channel


def get_instructions(
    channel: CondaChannel, subdirs: Subdirs
) -> Dict[Subdir, PatchInstructions]:
    return {subdir: channel.read_instructions(subdir) for subdir in subdirs}


def find_packages(
    channel: CondaChannel,
    requirements: Specs,
    exclusions: Optional[Specs] = None,
    disposables: Optional[Specs] = None,
    subdirs: Optional[Subdirs] = None,
    latest_versions: bool = False,
    latest_builds: bool = False,
    latest_roots: bool = False,
    console: Optional[Console] = None,
) -> Set[CondaPackage]:
    subdirs = subdirs if subdirs else get_default_subdirs()

    console = console if console else Console(quiet=True)
    display = Display(console)

    filters: List[PackageFilter] = []
    if requirements:
        filters.append(InclusionFilter(requirements))

    if exclusions:
        filters.append(ExclusionFilter(exclusions))

    if latest_versions:
        if latest_roots:
            filters.append(LatestVersionFilter())
        else:
            filters.append(LatestVersionFilter(requirements))

    if latest_builds:
        if latest_roots:
            filters.append(LatestVersionFilter())
        else:
            filters.append(LatestVersionFilter(requirements))

    query = crate_package_query(channel, subdirs, *filters)
    packages = resolve_packages(requirements, query)

    if disposables:
        filter_ = ExclusionFilter(disposables)
        packages = filter_(packages)

    with display.status("Search for packages"):
        results = set(packages)

    return results


def calculate_channel_difference(
    channel: CondaChannel,
    subdirs: Subdirs,
    packages: Iterable[CondaPackage],
    console: Optional[Console] = None,
) -> Tuple[Set[CondaPackage], Set[CondaPackage]]:

    console = console if console else Console(quiet=True)
    display = Display(console)

    with display.status("Calculating channel differences"):
        channel_packages = set(channel.iter_packages(subdirs))
        packages = set(packages)
        packages_to_add = packages - channel_packages
        packages_to_remove = channel_packages - packages

    return packages_to_add, packages_to_remove


def update_channel(
    target: LocalCondaChannel,
    packages_to_add: Iterable[CondaPackage],
    packages_to_remove: Iterable[CondaPackage],
    instructions: Optional[Dict[Subdir, PatchInstructions]] = None,
    console: Optional[Console] = None,
) -> None:

    console = console if console else Console(quiet=True)
    display = Display(console)

    target.setup()

    for package in display.progress(packages_to_add, "Downloading packages"):
        target.add_package(package)

    for package in display.progress(packages_to_remove, "Removing packages"):
        target.remove_package(package)

    if instructions:
        subdirs = instructions.keys()
        for subdir in display.progress(subdirs, "Updating patch instructions"):
            target.write_instructions(subdir, instructions[subdir])

    with display.status("Creating patch generator"):
        target.write_patch_generator()

    with display.status_monkeypatch_conda_index("Updating channel index"):
        target.update_index()


def create_patch(
    target: LocalCondaChannel,
    packages_to_add: Iterable[CondaPackage],
    packages_to_remove: Iterable[CondaPackage],
    instructions: Optional[Dict[Subdir, PatchInstructions]] = None,
    console: Optional[Console] = None,
) -> None:

    console = console if console else Console(quiet=True)
    display = Display(console)

    for package in display.progress(packages_to_add, "Downloading packages"):
        target.add_package(package)

    if instructions:
        subdirs = instructions.keys()
        for subdir in display.progress(subdirs, "Updating patch instructions"):
            instructions[subdir].remove.extend(pkg.fn for pkg in packages_to_remove)
            target.write_instructions(subdir, instructions[subdir])

    with display.status("Creating patch generator"):
        target.write_patch_generator()


def merge_patch(
    patch: LocalCondaChannel,
    target: LocalCondaChannel,
    console: Optional[Console] = None,
) -> None:
    console = console if console else Console(quiet=True)
    display = Display(console)

    target.merge(patch)

    with display.status_monkeypatch_conda_index("Updating channel index"):
        target.update_index()


def index_channel(target: LocalCondaChannel, console: Optional[Console] = None) -> None:
    console = console if console else Console(quiet=True)
    display = Display(console)
    with display.status_monkeypatch_conda_index("Updating channel index"):
        target.update_index()
