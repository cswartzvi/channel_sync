import datetime
import os

import click

from conda_local.cli.parameters import (
    CONTEXT_SETTINGS,
    ApplicationState,
    configuration_option,
    channel_option,
    latest_option,
    output_option,
    pass_state,
    quiet_option,
    requirements_argument,
    subdir_option,
    target_option,
    validate_option,
    exclusions_option,
    disposables_option
)
from conda_local.core import do_fetch, do_index, do_merge, do_query, do_sync


@click.command(
    short_help="Search for packages within an upstream anaconda channel.",
    context_settings=CONTEXT_SETTINGS,
)
@requirements_argument
@channel_option
@target_option
@exclusions_option
@disposables_option
@subdir_option
@latest_option
@validate_option
@output_option
@configuration_option
@quiet_option
@pass_state
def query(state: ApplicationState):
    """Search for packages and dependencies based on upstream REQUIREMENTS.

    \b
    Requirements and all other specifications are constructed using the anaconda package query syntax:
    https://docs.conda.io/projects/conda-build/en/latest/resources/package-spec.html#package-match-specifications
    """  # noqa: E501
    if state.output == "json":
        state.quiet = True

    do_query(
        channel_url=state.channel,
        target_url=state.target,
        requirements=state.requirements,
        exclusions=state.exclusions,
        disposables=state.disposables,
        subdirs=state.subdirs,
        latest=state.latest,
        validate=state.validate,
        output=state.output,
        quiet=state.quiet,
    )


@click.command(
    short_help="Fetch packages from an upstream channel to a patch folder.",
    context_settings=CONTEXT_SETTINGS,
)
@requirements_argument
@channel_option
@target_option
@exclusions_option
@disposables_option
@subdir_option
@click.option(
    "--name",
    type=click.types.STRING,
    help="Name of the patch. [patch_%Y%m%d_%H%M%S]",
)
@click.option(
    "--directory",
    default=".",
    type=click.types.Path(dir_okay=True, resolve_path=True),
    help="Parent directory where patches will be written [current directory]"
)
@latest_option
@validate_option
@configuration_option
@quiet_option
@pass_state
def fetch(state: ApplicationState, name: str, directory: str):
    """Fetch packages and dependencies based on upstream REQUIREMENTS.

    \b
    Requirements and all other specifications are constructed using the anaconda package query syntax:
    https://docs.conda.io/projects/conda-build/en/latest/resources/package-spec.html#package-match-specifications
    """  # noqa: E501

    if not name:
        now = datetime.datetime.now()
        name = f"patch_{now.strftime('%Y%m%d_%H%M%S')}"

    destination = os.path.join(directory, name)

    do_fetch(
        channel_url=state.channel,
        destination_url=destination,
        requirements=state.requirements,
        exclusions=state.exclusions,
        disposables=state.disposables,
        subdirs=state.subdirs,
        target_url=state.target,
        latest=state.latest,
        validate=state.validate,
        quiet=state.quiet,
    )


@click.command(
    short_help="Sync local and upstream anaconda channels.",
    context_settings=CONTEXT_SETTINGS,
)
@requirements_argument
@channel_option
@target_option
@exclusions_option
@disposables_option
@subdir_option
@latest_option
@validate_option
@output_option
@configuration_option
@quiet_option
@pass_state
def sync(state: ApplicationState):
    """Sync a TARGET and upstream channel based on REQUIREMENTS.

    \b
    Requirements and all other specifications are constructed using the anaconda package query syntax:
    https://docs.conda.io/projects/conda-build/en/latest/resources/package-spec.html#package-match-specifications
    """  # noqa: E501
    assert state.target is not None
    do_sync(
        channel_url=state.channel,
        target_url=state.target,
        requirements=state.requirements,
        exclusions=state.exclusions,
        disposables=state.disposables,
        subdirs=state.subdirs,
        latest=state.latest,
        validate=state.validate,
        quiet=state.quiet,
    )


@click.command(
    short_help="Merges a local anaconda channel with a patch folder.",
    context_settings=CONTEXT_SETTINGS,
)
@click.argument(
    "source",
    nargs=1,
    type=click.types.Path(exists=True, dir_okay=True, resolve_path=True),
)
@click.argument(
    "destination",
    nargs=1,
    type=click.types.Path(exists=True, dir_okay=True, resolve_path=True),
)
def merge(source, destination):
    """Merges SOURCE and DESTINATION local anaconda channel and updates index."""
    do_merge(source, destination)


@click.command(
    short_help="Index a local anaconda channel.",
    context_settings=CONTEXT_SETTINGS,
)
@click.argument(
    "target",
    nargs=1,
    type=click.types.Path(exists=True, dir_okay=True, resolve_path=True),
)
@configuration_option
@quiet_option
@pass_state
def index(state: ApplicationState, target: str):
    """Update the package index of a local TARGET channel."""
    do_index(target_url=target, quiet=state.quiet)
