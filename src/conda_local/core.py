from typing import Iterable

from rich.console import Console

from conda_local.adapt.subdir import get_default_subdirs
from conda_local.adapt.channel import CondaChannel, LocalCondaChannel
from conda_local.output import print_output
from conda_local.progress import iterate_progress, start_status
from conda_local.resolve import resolve_packages


def do_fetch(
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

    with start_status(f"Searching [bold cyan]{channel.name}", console=console):
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

    message = "Downloading packages "
    for package in iterate_progress(results.to_add, message, console=console):
        destination.add_package(package)

    message = "Updating instructions"
    for subdir in iterate_progress(subdirs, message, console=console):
        instructions = channel.read_instructions(subdir)
        instructions.update(remove=list(pkg.fn for pkg in results.to_remove))
        destination.write_instructions(subdir, instructions)

    with start_status("Creating patch generator", console=console):
        destination.write_patch_generator()

    console.print(f"Patch location: [bold cyan]{destination_url}")
    if console.quiet:
        print(destination_url)


def do_index(target_url: str, quiet: bool = True) -> None:
    console = Console(quiet=quiet, color_system="windows")
    target = LocalCondaChannel(target_url)
    with start_status("Updating index", console=console):
        target.update_index()


def do_query(
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

    with start_status(f"Searching [bold cyan]{channel.name}", console=console):
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


def do_sync(
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
    with start_status(f"Searching [bold cyan]{channel.name}", console=console):
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

    message = "Downloading packages"
    for package in iterate_progress(results.to_add, message, console=console):
        target.add_package(package)

    message = "Removing packages"
    for package in iterate_progress(results.to_remove, message, console=console):
        target.remove_package(package)

    message = "Downloading instructions"
    for subdir in iterate_progress(subdirs, message, console=console):
        instructions = channel.read_instructions(subdir)
        target.write_instructions(subdir, instructions)

    with start_status("Creating patch generator", console=console):
        target.write_patch_generator()

    with start_status("Updating index", console=console):
        target.update_index()


def do_merge(
    source_url: str,
    destination_url: str,
    quiet: bool = True,
) -> None:
    source = LocalCondaChannel(source_url)
    destination = LocalCondaChannel(destination_url)
    console = Console(quiet=quiet, color_system="windows")

    with start_status("Merging local channels", console=console):
        destination.merge(source)

    destination.update_index()
