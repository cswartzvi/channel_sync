from typing import Iterable, Optional

from rich.console import Console

from conda_local.models import get_default_subdirs
from conda_local.models.channel import CondaChannel, LocalCondaContainer
from conda_local.models.specification import CondaSpecification
from conda_local.output import print_output
from conda_local.progress import iterate_progress, start_status
from conda_local.resolve import resolve_packages


def do_fetch(
    channel: CondaChannel,
    target: LocalCondaContainer,
    requirements: Iterable[CondaSpecification],
    exclusions: Optional[Iterable[CondaSpecification]] = None,
    disposables: Optional[Iterable[CondaSpecification]] = None,
    subdirs: Optional[Iterable[str]] = None,
    latest: bool = True,
    validate: bool = True,
    console: Optional[Console] = None,
) -> None:

    exclusions = exclusions if exclusions else []
    disposables = disposables if disposables else []
    subdirs = subdirs if subdirs else get_default_subdirs()

    target.setup()
    reference = CondaChannel(target.url)

    with start_status(f"Searching [bold cyan]{channel.name}", console=console):
        results = resolve_packages(
            channel=channel,
            subdirs=subdirs,
            requirements=requirements,
            exclusions=exclusions,
            disposables=disposables,
            reference=reference,
            latest=latest,
            validate=validate,
        )

    message = "Downloading packages "
    for package in iterate_progress(results.to_add, message, console=console):
        target.add_package(package)

    message = "Patching instructions"
    for subdir in iterate_progress(subdirs, message, console=console):
        instructions = channel.read_patch_instructions(subdir)
        instructions.update(remove=list(pkg.fn for pkg in results.to_remove))
        target.write_instructions(subdir, instructions)

    with start_status("Creating patch generator", console=console):
        target.write_patch_generator()


def do_index(target: LocalCondaContainer, console: Optional[Console] = None) -> None:
    target.update_index()


def do_query(
    channel: CondaChannel,
    requirements: Iterable[CondaSpecification],
    exclusions: Optional[Iterable[CondaSpecification]] = None,
    disposables: Optional[Iterable[CondaSpecification]] = None,
    subdirs: Optional[Iterable[str]] = None,
    target: Optional[LocalCondaContainer] = None,
    latest: bool = True,
    validate: bool = True,
    output: str = "summary",
    console: Optional[Console] = None,
) -> None:

    exclusions = exclusions if exclusions else []
    disposables = disposables if disposables else []
    subdirs = subdirs if subdirs else get_default_subdirs()

    reference = None
    if target is not None and target.is_setup():
        reference = CondaChannel(target.url)

    with start_status(f"Searching [bold cyan]{channel.name}", console=console):
        results = resolve_packages(
            channel=channel,
            subdirs=subdirs,
            requirements=requirements,
            exclusions=exclusions,
            disposables=disposables,
            reference=reference,
            latest=latest,
            validate=validate,
        )

    print_output(output, results)


def do_sync(
    channel: CondaChannel,
    target: LocalCondaContainer,
    requirements: Iterable[CondaSpecification],
    exclusions: Optional[Iterable[CondaSpecification]] = None,
    disposables: Optional[Iterable[CondaSpecification]] = None,
    subdirs: Optional[Iterable[str]] = None,
    latest: bool = True,
    validate: bool = True,
    console: Optional[Console] = None,
) -> None:

    do_fetch(
        channel=channel,
        target=target,
        requirements=requirements,
        exclusions=exclusions,
        disposables=disposables,
        subdirs=subdirs,
        latest=latest,
        validate=validate,
        console=console,
    )

    do_index(target, console)


def do_merge(
    source: LocalCondaContainer,
    destination: LocalCondaContainer,
    console: Optional[Console] = None,
) -> None:
    with start_status("Merging local channels", console=console):
        destination.merge(source)
    destination.update_index()
