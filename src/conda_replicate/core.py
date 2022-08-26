import datetime
import os
from typing import Iterable, Optional, Set, Tuple

from rich.console import Console
from rich.table import Table

from conda_replicate.adapters.channel import CondaChannel
from conda_replicate.adapters.channel import LocalCondaChannel
from conda_replicate.adapters.package import CondaPackage
from conda_replicate.adapters.subdir import get_default_subdirs
from conda_replicate.display import Display
from conda_replicate.output import print_output
from conda_replicate.resolve import Parameters
from conda_replicate.resolve import Resolver


def find_packages(
    channel: CondaChannel,
    requirements: Iterable[str],
    exclusions: Iterable[str],
    disposables: Iterable[str],
    subdirs: Iterable[str],
    target: Optional[CondaChannel] = None,
) -> Tuple[Set[CondaPackage], Set[CondaPackage]]:
    """Performs package resolution on an anaconda channel based on specified parameters.

    Args:
        channel:
        requirements: An iterable of anaconda match specifications that defined the
            requirements of package resolution - which packages should be included
            and what versions / builds of those packages are allowed. Package
            resolution is designed to be a selective process, so if a particular
            package does note match a requirement (example: package 'A v0.2' does
            not match 'A >=1.0') then it will not be included in the solution.
        constraints (optional): An iterable of anaconda match specifications that
            defined additional constraints on package resolution. Constraints are
            permissive, meaning that a candidate is considered unconstrained if there
            are no match specifications for the package type in question. However,
            if one or more match specification exists for a candidate that package
            is considered constrained if it fails to match any of the specifications.
        subdirs (optional): Platform sub-directories where package resolution should
            take place. If None, then all default
        target (optional):
        latest:

    Returns:
        A tuple of packages to add and packages to remove.
    """

    parameters = Parameters(requirements, exclusions, disposables, subdirs)
    resolver = Resolver(channel)
    packages = set(resolver.resolve(parameters))

    to_add, to_remove = set(), set()
    if target is None or not target.is_queryable:
        to_add = packages
    else:
        existing_packages = set(target.iter_packages(subdirs))
        to_add = packages - existing_packages
        to_remove = existing_packages - packages

    return to_add, to_remove


def run_patch(
    channel_url: str,
    requirements: Iterable[str],
    exclusions: Iterable[str],
    disposables: Iterable[str],
    subdirs: Iterable[str],
    name: str = "",
    parent: str = "",
    target_url: str = "",
    quiet: bool = True,
) -> None:
    channel = CondaChannel(channel_url)
    target = CondaChannel(target_url) if target_url else None
    subdirs = subdirs if subdirs else get_default_subdirs()

    if not name:
        now = datetime.datetime.now()
        name = f"patch_{now.strftime('%Y%m%d_%H%M%S')}"
    path = os.path.join(parent, name)
    destination = LocalCondaChannel(path)
    destination.setup()

    console = Console(quiet=quiet, color_system="windows")
    display = Display(console)
    table = Table(show_header=False, box=None)
    table.add_row("Channel", channel.url)
    table.add_row("Target", target.url if target else "N/A")
    table.add_row("Subdirs", ", ".join(subdirs))
    table.add_row("Patch", str(destination.path.resolve()))
    console.print(table)
    console.print("")

    with display.status("Searching for packages"):
        to_add, to_remove = find_packages(
            channel=channel,
            subdirs=subdirs,
            requirements=requirements,
            exclusions=exclusions,
            disposables=disposables,
            target=target,
        )

    if to_add:
        for package in display.progress(to_add, "Downloading packages"):
            destination.add_package(package)

    for subdir in display.progress(subdirs, "Updating patch instructions"):
        instructions = channel.read_instructions(subdir)
        instructions.remove.extend(pkg.fn for pkg in to_remove)
        destination.write_instructions(subdir, instructions)

    with display.status("Creating patch generator"):
        destination.write_patch_generator()


def run_index(channel_url: str, quiet: bool = True) -> None:
    channel = LocalCondaChannel(channel_url)
    console = Console(quiet=quiet, color_system="windows")
    display = Display(console)
    with display.status_monkeypatch_conda_index("Updating channel index"):
        channel.update_index()


def run_search(
    channel_url: str,
    requirements: Iterable[str],
    exclusions: Iterable[str],
    disposables: Iterable[str],
    subdirs: Iterable[str],
    target_url: str = "",
    quiet: bool = True,
    output: str = "summary",
) -> None:

    channel = CondaChannel(channel_url)
    target = LocalCondaChannel(target_url) if target_url else None
    subdirs = subdirs if subdirs else get_default_subdirs()

    quiet = output == "json"  # disable animation for json
    console = Console(quiet=quiet, color_system="windows")
    display = Display(console)

    table = Table(show_header=False, box=None)
    table.add_row("Channel", channel.url)
    table.add_row("Target", target.url if target else "N/A")
    table.add_row("Subdirs", ", ".join(subdirs))
    console.print(table)
    console.print("")

    disable = output == "json"  # disable animation for json
    display = Display(console, disable)

    with display.status("Searching for packages"):
        to_add, to_remove = find_packages(
            channel=channel,
            subdirs=subdirs,
            requirements=requirements,
            exclusions=exclusions,
            disposables=disposables,
            target=target,
        )

    # Output should be displayed regardless of quiet=True
    print_output(output, to_add, to_remove)


def run_update(
    channel_url: str,
    requirements: Iterable[str],
    exclusions: Iterable[str],
    disposables: Iterable[str],
    subdirs: Iterable[str],
    target_url: str,
    quiet: bool = True,
) -> None:

    channel = CondaChannel(channel_url)
    target = LocalCondaChannel(target_url)
    subdirs = subdirs if subdirs else get_default_subdirs()

    console = Console(quiet=quiet, color_system="windows")
    display = Display(console)
    table = Table(show_header=False, box=None)
    table.add_row("Channel", channel.url)
    table.add_row("Target", str(target.path.resolve()))
    table.add_row("Subdirs", ", ".join(subdirs))
    console.print(table)
    console.print("")

    target.setup()
    with display.status("Searching for packages"):
        to_add, to_remove = find_packages(
            channel=channel,
            target=target,
            subdirs=subdirs,
            requirements=requirements,
            exclusions=exclusions,
            disposables=disposables,
        )

    if to_add:
        for package in display.progress(to_add, "Downloading packages"):
            target.add_package(package)

    if to_remove:
        for package in display.progress(to_remove, "Removing packages"):
            target.remove_package(package)

    for subdir in display.progress(subdirs, "Updating patch instructions"):
        instructions = channel.read_instructions(subdir)
        target.write_instructions(subdir, instructions)

    with display.status("Creating patch generator"):
        target.write_patch_generator()

    with display.status_monkeypatch_conda_index("Updating channel index"):
        target.update_index()


def run_merge(
    patch_url: str,
    target_url: str,
    quiet: bool = True,
) -> None:
    patch = LocalCondaChannel(patch_url)
    channel = LocalCondaChannel(target_url)
    console = Console(quiet=quiet, color_system="windows")

    display = Display(console=console)

    with display.status("Merging patch into channel"):
        channel.merge(patch)

    with display.status_monkeypatch_conda_index("Updating channel index"):
        channel.update_index()
