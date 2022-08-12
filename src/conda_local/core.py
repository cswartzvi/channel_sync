from typing import Iterable

from rich.console import Console

from conda_local.adapters.channel import CondaChannel
from conda_local.adapters.channel import LocalCondaChannel
from conda_local.adapters.subdir import get_default_subdirs
from conda_local.output import print_output
from conda_local.progress import iterate_progress
from conda_local.progress import start_index_monkeypatch
from conda_local.progress import start_status
from conda_local.resolve import resolve_packages


def run_patch(
    channel_url: str,
    destination_url: str,
    requirements: Iterable[str],
    exclusions: Iterable[str],
    disposables: Iterable[str],
    subdirs: Iterable[str],
    target_url: str = "",
    latest: bool = True,
    validate: bool = True,
    quiet: bool = True,
) -> None:

    channel = CondaChannel(channel_url)
    target = CondaChannel(target_url) if target_url else None
    subdirs = subdirs if subdirs else get_default_subdirs()
    console = Console(quiet=quiet, color_system="windows")

    destination = LocalCondaChannel(destination_url)
    destination.setup()

    with start_status(console, f"Searching {channel.name}"):
        results = resolve_packages(
            channel=channel,
            subdirs=subdirs,
            requirements=requirements,
            exclusions=exclusions,
            disposables=disposables,
            target=target,
            latest=latest,
            validate=validate,
        )

    if results.to_add:
        message = "Downloading packages"
        for package in iterate_progress(results.to_add, console, message, length=20):
            destination.add_package(package)

    message = "Updating instructions"
    for subdir in iterate_progress(subdirs, console, message, length=20):
        instructions = channel.read_instructions(subdir)
        instructions.update(remove=list(pkg.fn for pkg in results.to_remove))
        destination.write_instructions(subdir, instructions)

    with start_status(console, "Creating patch generator"):
        destination.write_patch_generator()

    console.print(f"Patch location: {destination_url}")
    if console.quiet:
        print(destination_url)


def run_index(target_url: str, quiet: bool = True) -> None:
    target = LocalCondaChannel(target_url)
    console = Console(quiet=quiet, color_system="windows")
    with start_index_monkeypatch(console, "Indexing subdirs"):
        target.update_index()


def run_search(
    channel_url: str,
    requirements: Iterable[str],
    exclusions: Iterable[str],
    disposables: Iterable[str],
    subdirs: Iterable[str],
    target_url: str = "",
    latest: bool = True,
    validate: bool = False,
    quiet: bool = True,
    output: str = "summary",
) -> None:

    channel = CondaChannel(channel_url)
    target = LocalCondaChannel(target_url) if target_url else None
    subdirs = subdirs if subdirs else get_default_subdirs()
    console = Console(quiet=quiet, color_system="windows")

    with start_status(console, f"Searching {channel.name}"):
        results = resolve_packages(
            channel=channel,
            subdirs=subdirs,
            requirements=requirements,
            exclusions=exclusions,
            disposables=disposables,
            target=target,
            latest=latest,
            validate=validate,
        )

    print_output(output, results)


def run_sync(
    channel_url: str,
    target_url: str,
    requirements: Iterable[str],
    exclusions: Iterable[str],
    disposables: Iterable[str],
    subdirs: Iterable[str],
    latest: bool = True,
    validate: bool = True,
    quiet: bool = True,
) -> None:

    channel = CondaChannel(channel_url)
    target = LocalCondaChannel(target_url)
    subdirs = subdirs if subdirs else get_default_subdirs()
    console = Console(quiet=quiet, color_system="windows")

    target.setup()
    with start_status(console, f"Searching {channel.name}"):
        results = resolve_packages(
            channel=channel,
            target=target,
            subdirs=subdirs,
            requirements=requirements,
            exclusions=exclusions,
            disposables=disposables,
            latest=latest,
            validate=validate,
        )

    if results.to_add:
        message = "Downloading packages"
        for package in iterate_progress(results.to_add, console, message, length=21):
            target.add_package(package)

    if results.to_remove:
        message = "Removing packages"
        for package in iterate_progress(results.to_remove, console, message, length=21):
            target.remove_package(package)

    message = "Copying instructions"
    for subdir in iterate_progress(subdirs, console, message, length=21):
        instructions = channel.read_instructions(subdir)
        target.write_instructions(subdir, instructions)

    with start_status(console, "Creating patch generator"):
        target.write_patch_generator()

    with start_index_monkeypatch(console, "Indexing channel subdirs"):
        target.update_index()


def run_merge(
    source_url: str,
    destination_url: str,
    quiet: bool = True,
) -> None:
    source = LocalCondaChannel(source_url)
    destination = LocalCondaChannel(destination_url)
    console = Console(quiet=quiet, color_system="windows")

    with start_status(console, "Merging local channels"):
        destination.merge(source)

    destination.update_index()
