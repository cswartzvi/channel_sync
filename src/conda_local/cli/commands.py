import datetime
import os

import click

from conda_local.cli.parameters import CONTEXT_SETTINGS
from conda_local.cli.parameters import ApplicationState
from conda_local.cli.parameters import channel_option
from conda_local.cli.parameters import configuration_option
from conda_local.cli.parameters import disposables_option
from conda_local.cli.parameters import exclusions_option
from conda_local.cli.parameters import latest_option
from conda_local.cli.parameters import output_option
from conda_local.cli.parameters import pass_state
from conda_local.cli.parameters import quiet_option
from conda_local.cli.parameters import requirements_argument
from conda_local.cli.parameters import subdir_option
from conda_local.cli.parameters import target_option
from conda_local.cli.parameters import validate_option
from conda_local.core import run_patch
from conda_local.core import run_index
from conda_local.core import run_merge
from conda_local.core import run_search
from conda_local.core import run_sync


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
def search(state: ApplicationState):
    """Search for packages and dependencies based on upstream REQUIREMENTS.

    \b
    Requirements and all other specifications are constructed using the anaconda package query syntax:
    https://docs.conda.io/projects/conda-build/en/latest/resources/package-spec.html#package-match-specifications
    """  # noqa: E501
    if state.output == "json":
        state.quiet = True

    run_search(
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
    short_help="Create a patch folder from an upstream channel.",
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
    help="Parent directory where patches will be written [current directory]",
)
@latest_option
@validate_option
@configuration_option
@quiet_option
@pass_state
def patch(state: ApplicationState, name: str, directory: str):
    """Create a patch folder from an upstream anaconda channel based on REQUIREMENTS.

    \b
    Requirements and all other specifications are constructed using the anaconda package query syntax:
    https://docs.conda.io/projects/conda-build/en/latest/resources/package-spec.html#package-match-specifications
    """  # noqa: E501

    if not name:
        now = datetime.datetime.now()
        name = f"patch_{now.strftime('%Y%m%d_%H%M%S')}"

    destination = os.path.join(directory, name)

    run_patch(
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
    """Sync a local TARGET anaconda channel with an upstream channel based on REQUIREMENTS.

    \b
    Requirements and all other specifications are constructed using the anaconda package query syntax:
    https://docs.conda.io/projects/conda-build/en/latest/resources/package-spec.html#package-match-specifications
    """  # noqa: E501
    assert state.target is not None
    run_sync(
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
    run_merge(source, destination)


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
    run_index(target_url=target, quiet=state.quiet)
