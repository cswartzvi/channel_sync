import datetime
from pathlib import Path

import click
from rich.console import Console

from conda_local.cli.parameters import (
    CONTEXT_SETTINGS,
    ApplicationState,
    channel_options,
    common_search_options,
    configuration_option,
    destination_argument,
    output_option,
    pass_state,
    patch_options,
    quiet_option,
    requirements_argument,
    source_argument,
    target_argument,
)
from conda_local.core import do_fetch, do_index, do_merge, do_query, do_sync
from conda_local.models.channel import LocalCondaContainer


@click.command(
    short_help="Search for packages within an upstream anaconda channel.",
    context_settings=CONTEXT_SETTINGS,
)
@requirements_argument
@channel_options
@common_search_options
@output_option
@configuration_option
@pass_state
def query(state: ApplicationState):
    """Search for packages and dependencies based on upstream REQUIREMENTS.

    \b
    Requirements and all other specifications are constructed using the anaconda package query syntax:
    https://docs.conda.io/projects/conda-build/en/latest/resources/package-spec.html#package-match-specifications
    """  # noqa: E501
    console = Console(quiet=state.quiet, color_system="windows")

    do_query(
        channel=state.channel,
        requirements=state.requirements,
        exclusions=state.exclusions,
        disposables=state.disposables,
        subdirs=state.subdirs,
        target=state.target,
        latest=state.latest,
        validate=state.validate,
        output=state.output,
        console=console,
    )


@click.command(
    short_help="Fetch packages from an upstream anaconda channel.",
    context_settings=CONTEXT_SETTINGS,
)
@requirements_argument
@channel_options
@common_search_options
@patch_options
@quiet_option
@configuration_option
@pass_state
def fetch(state: ApplicationState):
    """Fetch packages and dependencies based on upstream REQUIREMENTS.

    \b
    Requirements and all other specifications are constructed using the anaconda package query syntax:
    https://docs.conda.io/projects/conda-build/en/latest/resources/package-spec.html#package-match-specifications
    """  # noqa: E501
    console = Console(quiet=state.quiet, color_system="windows")

    patch_directory = Path(state.patch_directory).resolve()

    patch_name = state.patch_name
    if not patch_name:
        now = datetime.datetime.now()
        patch_name = f"patch_{now.strftime('%Y%m%d_%H%M%S')}"

    target = LocalCondaContainer(patch_directory / patch_name)

    do_fetch(
        channel=state.channel,
        target=target,
        requirements=state.requirements,
        exclusions=state.exclusions,
        disposables=state.disposables,
        subdirs=state.subdirs,
        latest=state.latest,
        validate=state.validate,
        console=console,
    )

    console.print(f"Patch location: [bold cyan]{target.path.resolve()}")
    if console.quiet:
        print(target.path.resolve())


@click.command(
    short_help="Sync local and upstream anaconda channels.",
    context_settings=CONTEXT_SETTINGS,
)
@target_argument
@requirements_argument
@channel_options
@common_search_options
@quiet_option
@configuration_option
@pass_state
def sync(state: ApplicationState):
    """Sync a TARGET and upstream channel based on REQUIREMENTS.

    \b
    Requirements and all other specifications are constructed using the anaconda package query syntax:
    https://docs.conda.io/projects/conda-build/en/latest/resources/package-spec.html#package-match-specifications
    """  # noqa: E501
    console = Console(quiet=state.quiet, color_system="windows")

    assert state.target is not None
    do_sync(
        channel=state.channel,
        target=state.target,
        requirements=state.requirements,
        exclusions=state.exclusions,
        disposables=state.disposables,
        subdirs=state.subdirs,
        latest=state.latest,
        validate=state.validate,
        console=console,
    )


@click.command(
    short_help="Merges and updates local anaconda channels.",
    context_settings=CONTEXT_SETTINGS,
)
@source_argument
@destination_argument
@pass_state
def merge(state: ApplicationState):
    """Merges SOURCE and DESTINATION anaconda channel and updates index.."""
    console = Console(quiet=state.quiet, color_system="windows")

    assert state.source is not None
    assert state.destination is not None
    do_merge(state.source, state.destination, console)


@click.command(
    short_help="Index a local anaconda channel.",
    context_settings=CONTEXT_SETTINGS,
)
@target_argument
@requirements_argument
@channel_options
@common_search_options
@quiet_option
@configuration_option
@pass_state
def index(state: ApplicationState):
    """Update the package index of a local TARGET channel."""
    console = Console(quiet=state.quiet, color_system="windows")

    assert state.target is not None
    do_index(state.target, console)
