from pathlib import Path
from typing import Iterable, List, Optional, TypeVar

from rich.console import Console

from conda_local.models.channel import CondaChannel, LocalCondaContainer
from conda_local.models.specification import CondaSpecification
from conda_local.progress import iterate_progress, start_status
from conda_local.resolve import ResolvedPackages, resolve_packages

T = TypeVar("T")


def fetch(
    channel: str,
    requirements: Iterable[str],
    directory: str,
    name: str,
    constraints: Optional[Iterable[str]] = None,
    disposables: Optional[Iterable[str]] = None,
    subdirs: Optional[Iterable[str]] = None,
    reference: str = "",
    latest: bool = True,
    validate: bool = True,
    quiet: bool = False,
) -> LocalCondaContainer:
    console = Console(quiet=quiet, color_system="windows")

    upstream = CondaChannel(channel)
    subdirs = _ensure_iterable(subdirs)

    path = Path(directory).resolve() / name
    container = LocalCondaContainer(path)

    if container.path.exists():
        if not reference:
            reference = container.url

    path.parent.mkdir(exist_ok=True, parents=True)

    results = query(
        channel=upstream.url,
        requirements=requirements,
        constraints=constraints,
        disposables=disposables,
        subdirs=subdirs,
        reference=reference,
        latest=latest,
        validate=validate,
    )

    message = "Downloading packages "
    for package in iterate_progress(results.to_add, message, console=console):
        container.add_package(package)

    message = "Patching instructions"
    for subdir in iterate_progress(subdirs, message, console=console):
        instructions = upstream.read_patch_instructions(subdir)
        instructions.update(remove=list(pkg.fn for pkg in results.to_remove))
        container.write_instructions(subdir, instructions)

    with start_status("Creating patch generator", console=console):
        container.write_patch_generator()

    console.print(f"Patch location: [bold cyan]{container.path.resolve()}")
    if console.quiet:
        print(container.path.resolve())

    return container


def query(
    channel: str,
    requirements: Iterable[str],
    constraints: Optional[Iterable[str]] = None,
    disposables: Optional[Iterable[str]] = None,
    subdirs: Optional[Iterable[str]] = None,
    reference: str = "",
    latest: bool = True,
    validate: bool = True,
    quiet: bool = False,
) -> ResolvedPackages:

    console = Console(quiet=quiet, color_system="windows")

    upstream = CondaChannel(channel)

    with start_status(f"Searching [bold cyan]{upstream.name}", console=console):
        results = resolve_packages(
            channel=upstream,
            subdirs=_ensure_iterable(subdirs),
            requirements=_make_specs(requirements),
            constraints=_make_specs(constraints),
            disposables=_make_specs(disposables),
            reference=CondaChannel(reference) if reference else None,
            latest=latest,
            validate=validate,
        )
    return results


def update(
    channel: str,
    target: str,
    requirements: Iterable[str],
    constraints: Optional[Iterable[str]] = None,
    disposables: Optional[Iterable[str]] = None,
    subdirs: Optional[Iterable[str]] = None,
    reference: str = "",
    latest: bool = True,
    validate: bool = True,
    quiet: bool = False,
) -> LocalCondaContainer:
    path = Path(target).resolve()

    container = fetch(
        channel=channel,
        directory=str(path.parent),
        name=path.name,
        requirements=requirements,
        constraints=constraints,
        disposables=disposables,
        subdirs=subdirs,
        reference=reference,
        latest=latest,
        validate=validate,
        quiet=quiet
    )

    container.update_index()

    return container


def index(target: str, quite: bool = False) -> None:
    container = LocalCondaContainer(path)



def _make_specs(items: Optional[Iterable[str]]) -> Iterable[CondaSpecification]:
    specs: List[CondaSpecification] = []
    for item in _ensure_iterable(items):
        spec = CondaSpecification(item)
        specs.append(spec)
    return specs


def _ensure_iterable(items: Optional[Iterable[T]]) -> Iterable[T]:
    if items is None:
        return []
    return items
