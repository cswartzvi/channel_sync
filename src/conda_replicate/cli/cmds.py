from dis import Instruction
from operator import sub
from typing import TYPE_CHECKING

import pydantic
from rich.console import Console

from conda_replicate import CondaReplicateException
from conda_replicate import __version__
from conda_replicate.cli.params import channel_option
from conda_replicate.cli.params import requirements_argument
from conda_replicate.cli.params import target_callback
from conda_replicate.cli.params import exclusions_option
from conda_replicate.cli.params import disposables_option
from conda_replicate.cli.params import subdirs_option
from conda_replicate.cli.params import configuration_option
from conda_replicate.cli.params import latest_versions_option
from conda_replicate.cli.params import latest_builds_option
from conda_replicate.cli.params import quiet_option
from conda_replicate.cli.params import debug_option
from conda_replicate.cli.state import AppState
from conda_replicate.cli.state import pass_state
from conda_replicate.api import calculate_channel_difference, find_packages
from conda_replicate.api import get_channel
from conda_replicate.api import get_local_channel
from conda_replicate.api import get_instructions
from conda_replicate.api import create_patch
from conda_replicate.api import index_channel
from conda_replicate.api import merge_patch
from conda_replicate.api import update_channel
from conda_replicate.output import print_output

# mypy has issues with the dynamic nature of rich-click
if TYPE_CHECKING:  # pragma: no cover
    import click
else:
    import rich_click as click

    click.rich_click.MAX_WIDTH = 120
    click.rich_click.STYLE_ABORTED = "bold red"
    click.rich_click.STYLE_DEPRECATED = "bold red"
    click.rich_click.STYLE_ERRORS_PANEL_BORDER = "bold red"
    click.rich_click.STYLE_OPTIONS_TABLE_BOX = "SIMPLE"
    click.rich_click.STYLE_OPTIONS_TABLE_LEADING = 1
    click.rich_click.STYLE_REQUIRED_LONG = "bold red"
    click.rich_click.STYLE_REQUIRED_SHORT = "bold red"
    click.rich_click.STYLE_ERRORS_SUGGESTION = "bold"
    click.rich_click.USE_MARKDOWN = True


# Root command
@click.group()
@click.decorators.version_option(prog_name="conda-local", version=__version__)
def app():
    """Synthesize local anaconda channels from upstream sources."""
    pass


# Sub-command: query
@app.command(short_help="Search an upstream channel for packages and report results.")
@requirements_argument
@channel_option
@click.option(
    "-t",
    "--target",
    default="",
    type=click.types.STRING,
    callback=target_callback,
    is_eager=False,
    expose_value=False,  # handled in callback
    help=(
        "Target anaconda channel. When specified, this channel will act as a "
        "baseline for the package search process - only package differences "
        "(additions or deletions) will be reported to the user."
    ),
)
@exclusions_option
@disposables_option
@subdirs_option
@click.option(
    "--output",
    default="table",
    metavar="OUTPUT",
    type=click.types.Choice(["table", "list", "json"]),
    help=(
        "Specifies the format of the search results. Allowed values: "
        "{table, list, json}."
    ),
)
@latest_versions_option
@latest_builds_option
@configuration_option
@quiet_option
@debug_option
@pass_state
@pydantic.validate_arguments
def query(state: AppState, output: str):
    """
    Search an upstream channel for the specified package REQUIREMENTS and report
    results.

    - Resulting packages are reported to the user in the specified output form
    (see --output)

    - Include both direct and transitive dependencies of required packages

    Package requirement notes:
    - Requirements are constructed using the anaconda package query syntax

    - Unsatisfied requirements will raise an error by default (see --no-validate)

    - Requirements specified on the command line *augment* those specified in a
    configuration file

    """  # noqa: E501

    console = Console(quiet=state.quiet)

    try:
        channel = get_channel(state.channel)
        packages = find_packages(
            channel=channel,
            requirements=sorted(state.requirements),
            exclusions=sorted(state.exclusions),
            disposables=sorted(state.disposables),
            subdirs=sorted(state.subdirs),
            latest_versions=state.latest_versions,
            console=console,
        )
        if state.target:
            target = get_local_channel(state.target, setup=False)
            packages_to_add, packages_to_remove = calculate_channel_difference(
                target, state.subdirs, packages, console
            )
            print_output(output, packages_to_add, packages_to_remove)
        else:
            print_output(output, packages_to_add, {})
    except CondaReplicateException as exception:
        _process_application_exception(exception)


# Sub-command: update
@app.command(short_help="Update a local channel from an upstream channel.")
@requirements_argument
@click.option(
    "-t",
    "--target",
    type=click.types.STRING,
    callback=target_callback,
    is_eager=False,
    expose_value=False,  # handled in callback
    help=(
        "Local anaconda channel where the update will occur. If this local channel "
        "already exists it will act as a baseline for the package search process - "
        "only package differences (additions or deletions) will be updated."
    ),
)
@channel_option
@exclusions_option
@disposables_option
@subdirs_option
@latest_versions_option
@latest_builds_option
@configuration_option
@quiet_option
@debug_option
@pass_state
@pydantic.validate_arguments
def update(state: AppState):
    """Update a local channel based on specified upstream package REQUIREMENTS.

    - Packages are downloaded or removed from the local channel prior to re-indexing

    - Includes both direct and transitive dependencies of required packages

    - Includes update to the platform specific patch instructions (hotfixes)

    Package requirement notes:
    - Requirements are constructed using the anaconda package query syntax

    - Unsatisfied requirements will raise an error by default (see --no-validate)

    - Requirements specified on the command line *augment* those specified in a
    configuration file
    """  # noqa: E501
    if not state.target:
        raise click.UsageError(
            "Target must be specified as '-t', '--target' or in a configuration file."
        )

    console = Console(quiet=state.quiet)

    try:
        channel = get_channel(state.channel)
        instructions = get_instructions(channel, subdirs=state.subdirs)
        target = get_local_channel(state.target, setup=False)

        packages = find_packages(
            channel=channel,
            requirements=sorted(state.requirements),
            exclusions=sorted(state.exclusions),
            disposables=sorted(state.disposables),
            subdirs=sorted(state.subdirs),
            latest_versions=state.latest_versions,
            console=console,
        )

        packages_to_add, packages_to_remove = calculate_channel_difference(
            target, state.subdirs, packages, console
        )

        update_channel(
            target=target,
            packages_to_add=packages_to_add,
            packages_to_remove=packages_to_remove,
            instructions=instructions,
            console=console
        )

    except CondaReplicateException as exception:
        _process_application_exception(exception)


# Sub-command: patch
@app.command(short_help="Create a patch from an upstream channel.")
@requirements_argument
@click.option(
    "-t",
    "--target",
    default="",
    type=click.types.STRING,
    callback=target_callback,
    is_eager=False,
    expose_value=False,  # handled in callback
    help=(
        "Target anaconda channel. When specified, this channel will act as a "
        "baseline for the package search process - only package differences "
        "(additions or deletions) will be included in the patch."
    ),
)
@click.option(
    "--name",
    default="",
    type=click.types.STRING,
    help="Name of the patch directory. [patch_%Y%m%d_%H%M%S]",
)
@click.option(
    "--parent",
    default=".",
    type=click.types.Path(dir_okay=True, resolve_path=True),
    help="Parent directory of the patch. [current directory]",
)
@channel_option
@exclusions_option
@disposables_option
@subdirs_option
@latest_versions_option
@latest_builds_option
@configuration_option
@quiet_option
@debug_option
@pass_state
@pydantic.validate_arguments
def patch(state: AppState, name: str, parent: str):
    """Create a patch from an upstream channel based on specified package REQUIREMENTS.

    - Packages are downloaded to a local patch directory (see --name and --parent)

    - Patches can be merged into existing local channels (see merge sub-command)

    - Includes both direct and transitive dependencies of required packages

    - Includes update to the platform specific patch instructions (hotfixes)

    Package requirement notes:
    - Requirements are constructed using the anaconda package query syntax

    - Unsatisfied requirements will raise an error by default (see --no-validate)

    - Requirements specified on the command line *augment* those specified in a
    configuration file
    """  # noqa: E501

    if not name:
        now = datetime.datetime.now()
        name = f"patch_{now.strftime('%Y%m%d_%H%M%S')}"
    path = os.path.join(parent, name)
    target = get_local_channel(path, setup=False)

    try:
        run_patch(
            channel_url=state.channel,
            requirements=sorted(state.requirements),
            exclusions=sorted(state.exclusions),
            disposables=sorted(state.disposables),
            subdirs=sorted(state.subdirs),
            name=name,
            parent=parent,
            target_url=state.target,
            quiet=state.quiet,
            latest=state.latest_versions,
        )
    except CondaReplicateException as exception:
        _process_application_exception(exception)


# Sub-command: merge
@app.command(short_help="Merge a patch into a local channel.")
@click.argument(
    "patch",
    nargs=1,
    type=click.types.Path(exists=True, dir_okay=True, resolve_path=True),
)
@click.argument(
    "channel",
    nargs=1,
    type=click.types.Path(exists=True, dir_okay=True, resolve_path=True),
)
@quiet_option
@debug_option
@pass_state
@pydantic.validate_arguments
def merge(state: AppState, patch: str, channel: str):
    """Merge a PATCH into a local CHANNEL and update the local package index."""
    try:
        run_merge(patch, channel, quiet=state.quiet)
    except CondaReplicateException as exception:
        _process_application_exception(exception)


# Sub-command: index
@app.command(short_help="Update the package index of a local channel.")
@click.argument(
    "channel",
    nargs=1,
    type=click.types.Path(exists=True, dir_okay=True, resolve_path=True),
)
@quiet_option
@debug_option
@pass_state
@pydantic.validate_arguments
def index(state: AppState, channel: str):
    """Update the package index of a local CHANNEL."""
    try:
        run_index(channel_url=channel, quiet=state.quiet)
    except CondaReplicateException as exception:
        _process_application_exception(exception)


def _process_application_exception(exception: CondaReplicateException) -> None:
    click.secho("\n\n ERROR: ", fg="red", bold=True, nl=False)
    click.secho(exception.args[0])
