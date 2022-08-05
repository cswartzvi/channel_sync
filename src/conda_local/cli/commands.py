import click
from rich.console import Console

from conda_local.cli.options import (
    CONTEXT_SETTINGS,
    AppState,
    channel_options,
    configuration_option,
    output_option,
    pass_state,
    patch_options,
    quiet_option,
    search_options,
    specifications_argument,
)
from conda_local.output import print_output
from conda_local.patch import (
    create_patch_generator,
    create_patch_instructions,
    fetch_package,
    update_patch_instructions,
)
from conda_local.progress import iterate_progress, start_status
from conda_local.resolve import resolve_packages


@click.command(
    short_help="Search an anaconda channel for packages",
    context_settings=CONTEXT_SETTINGS,
)
@specifications_argument
@channel_options
@search_options
@output_option
@configuration_option
@quiet_option
@pass_state
def search(state: AppState):
    """Search for packages and dependencies within an anaconda channel based on
    SPECIFICATIONS.

    \b
    Specifications are constructed using the anaconda match specification query syntax:
    https://docs.conda.io/projects/conda-build/en/latest/resources/package-spec.html#package-match-specifications
    """
    console = Console(quiet=state.quiet, color_system="windows")

    with start_status(f"Searching [bold cyan]{state.channel.name}", console=console):
        resolved = resolve_packages(
            channel=state.channel,
            subdirs=state.subdirs,
            requirements=state.requirements,
            constraints=state.constraints,
            disposables=state.disposables,
            reference=state.reference,
            latest=state.latest,
            validate=state.validate,
        )
    print_output(state.output, resolved)


@click.command(
    short_help="Fetch packages from an anaconda channel",
    context_settings=CONTEXT_SETTINGS,
)
@specifications_argument
@channel_options
@search_options
@patch_options
@quiet_option
@configuration_option
@pass_state
def fetch(state: AppState):
    """Fetch packages and dependencies from an anaconda channel based on SPECIFICATIONS.

    \b
    Specifications are constructed using the anaconda match specification query syntax:
    https://docs.conda.io/projects/conda-build/en/latest/resources/package-spec.html#package-match-specifications
    """
    console = Console(quiet=state.quiet, color_system="windows")

    with start_status(f"Searching [bold cyan]{state.channel.name}", console=console):
        resolved = resolve_packages(
            channel=state.channel,
            subdirs=state.subdirs,
            requirements=state.requirements,
            constraints=state.constraints,
            disposables=state.disposables,
            reference=state.reference,
            latest=state.latest,
            validate=state.validate,
        )

    patch = state.patch_directory.resolve() / state.patch_name
    patch.mkdir(exist_ok=True, parents=True)

    message = "Downloading packages "
    for package in iterate_progress(resolved.to_add, message, console=console):
        fetch_package(patch, package)

    message = "Patching instructions"
    for subdir in iterate_progress(state.subdirs, message, console=console):
        create_patch_instructions(patch, subdir, source=state.channel)
        update_patch_instructions(patch, removals=resolved.to_remove)

    with start_status("Creating patch generator", console=console):
        create_patch_generator(patch)

    console.print(f"Patch location: [bold cyan]{patch.resolve()}")
    if console.quiet:
        print(patch.resolve())
