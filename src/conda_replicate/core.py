import datetime
from optparse import Option
import os
from struct import pack
from typing import Dict, Iterable, Iterator, List, Optional, Set, Tuple

from rich.console import Console
from rich.table import Table

from conda_replicate._typing import Spec, Specs, Subdir, Subdirs
from conda_replicate.adapters.channel import CondaChannel
from conda_replicate.adapters.channel import LocalCondaChannel
from conda_replicate.adapters.channel import PatchInstructions
from conda_replicate.adapters.package import CondaPackage
from conda_replicate.adapters.subdir import get_default_subdirs
from conda_replicate.display import Display
from conda_replicate.output import print_output
from conda_replicate.resolve import resolve_packages
from conda_replicate.query import crate_package_query
from conda_replicate.query import ExclusionFilter
from conda_replicate.query import InclusionFilter
from conda_replicate.query import LatestVersionFilter
from conda_replicate.query import PackageFilter


def get_channel(url: str) -> CondaChannel:
    pass


def get_local_channel(url: str) -> CondaChannel:
    pass


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


def diff_packages(
    left: Iterable[CondaPackage],
    right: Iterable[CondaPackage],
    console: Optional[Console] = None,
) -> Tuple[Set[CondaPackage], Set[CondaPackage]]:

    console = console if console else Console(quiet=True)
    display = Display(console)

    with display.status("Search for packages"):
        left = set(left)
        right = set(right)
        only_in_left = left - right
        only_in_right = right - left

    return only_in_left, only_in_right


def update_channel(
    target: LocalCondaChannel,
    packages_to_add: Iterable[CondaPackage],
    packages_to_remove: Iterable[CondaPackage],
    instructions: Optional[Dict[str, PatchInstructions]] = None,
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
    packages_to_add: Iterable[CondaPackage],
    packages_to_remove: Iterable[CondaPackage],
    instructions: Optional[Dict[str, PatchInstructions]] = None,
    name: str = "",
    parent: str = "",
    console: Optional[Console] = None,
) -> None:

    console = console if console else Console(quiet=True)
    display = Display(console)

    if not name:
        now = datetime.datetime.now()
        name = f"patch_{now.strftime('%Y%m%d_%H%M%S')}"
    path = os.path.join(parent, name)
    destination = LocalCondaChannel(path)
    destination.setup()

    for package in display.progress(packages_to_add, "Downloading packages"):
        destination.add_package(package)

    for subdir in display.progress(subdirs, "Updating patch instructions"):
        instructions = channel.read_instructions(subdir)
        instructions.remove.extend(pkg.fn for pkg in packages_to_remove)
        destination.write_instructions(subdir, instructions)

    with display.status("Creating patch generator"):
        destination.write_patch_generator()


def merge_patch(
    patch: LocalCondaChannel,
    target: LocalCondaChannel,
    console: Optional[Console] = None,
) -> None:
    console = console if console else Console(quiet=True)
    display = Display(console)

    display = Display(console=console)

    target.merge(patch)

    with display.status_monkeypatch_conda_index("Updating channel index"):
        target.update_index()


def index_channel(target: LocalCondaChannel, console: Optional[Console] = None) -> None:
    console = console if console else Console(quiet=True)
    display = Display(console)
    with display.status_monkeypatch_conda_index("Updating channel index"):
        target.update_index()
