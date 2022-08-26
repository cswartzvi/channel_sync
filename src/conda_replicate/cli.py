import logging
import sys
from typing import TYPE_CHECKING, Any, Iterable, List

import pydantic
import yaml
from pydantic import BaseSettings
from pydantic import Field

from conda_replicate import CondaReplicateException
from conda_replicate import __version__
from conda_replicate.adapters.subdir import get_default_subdirs
from conda_replicate.adapters.subdir import get_known_subdirs
from conda_replicate.core import run_index
from conda_replicate.core import run_merge
from conda_replicate.core import run_patch
from conda_replicate.core import run_search
from conda_replicate.core import run_update

# mypy has issues with the dynamic nature of rich-click
if TYPE_CHECKING:
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

_DEFAULT_SUBDIRS = get_default_subdirs()
_KNOWN_SUBDIRS = get_known_subdirs()
_ALLOWED_SUBDIRS = [subdir for subdir in sorted(_KNOWN_SUBDIRS)]


class AppState(BaseSettings):
    """Persistent application state (valid for all sub-commands)."""

    debug: int = 0
    quiet: bool = True


pass_state = click.make_pass_decorator(AppState, ensure=True)


class Configuration(BaseSettings):
    """The current state of configuration file settings."""

    channel: str = ""
    target: str = ""
    requirements: List[str] = Field(default_factory=list)
    exclusions: List[str] = Field(default_factory=list)
    disposables: List[str] = Field(default_factory=list)
    subdirs: List[str] = Field(default_factory=list)


def check_configuration(name: str):
    """Returns a parameter callback function that checks configuration settings.

    When a configuration setting exists it is generally only used when the associated
    command line value is not specified. However, if the configuration setting is
    a list, the command line value is added to the end of the configuration setting,
    which is then returned the the calling site.
    """

    def callback(context: click.Context, parameter: click.Parameter, value: Any):
        configuration = context.find_object(Configuration)
        if configuration:
            setting = getattr(configuration, name)
            if isinstance(setting, list):
                assert isinstance(value, Iterable) and not isinstance(
                    value, str
                ), "command line value is not iterable"
                setting = setting[:]  # copy
                setting.extend(value)
                value = setting
            elif not value:
                value = setting
        return value

    return callback


channel_option = click.option(
    "-c",
    "--channel",
    "channel",
    default="conda-forge",
    type=click.types.STRING,
    callback=check_configuration("channel"),
    show_default=True,
    is_eager=False,
    help=(
        "Upstream anaconda channel. Can be specified using the canonical channel "
        "name on anaconda.org (conda-forge), a fully qualified URL "
        "(https://conda.anaconda.org/conda-forge/), or a local directory path."
    ),
)


exclusions_option = click.option(
    "--exclude",
    "exclusions",
    multiple=True,
    type=click.types.STRING,
    callback=check_configuration("exclusions"),
    is_eager=False,
    help=(
        "Packages excluded from the search process. Specified using the anaconda "
        "package query syntax. Multiple options may be passed at one time. "
    ),
)


disposables_option = click.option(
    "--dispose",
    "disposables",
    multiple=True,
    type=click.types.STRING,
    callback=check_configuration("disposables"),
    is_eager=False,
    help=(
        "Packages that are used in the search process but not included in the "
        "final results. Specified using the anaconda package query syntax. "
        "Multiple options may be passed at one time. "
    ),
)

subdirs_option = click.option(
    "--subdir",
    "subdirs",
    multiple=True,
    type=click.types.Choice(_KNOWN_SUBDIRS),
    callback=check_configuration("disposables"),
    default=_DEFAULT_SUBDIRS,
    metavar="SUBDIR",
    show_default=True,
    is_eager=False,
    help=(
        "Selected platform sub-directories. Multiple options may be passed at "
        f"one time. Allowed values: {{{', '.join(_ALLOWED_SUBDIRS)}}}."
    ),
)


def implicit_quiet_option(function):
    def callback(context: click.Context, parameter: click.Parameter, value: Any):
        state = context.ensure_object(AppState)
        state.quiet = True if state.debug > 1 else value
        return value

    return click.option(
        "--quiet",
        is_flag=True,
        default=False,
        type=click.types.BOOL,
        callback=callback,
        expose_value=False,  # Must be False!
        help="Quite mode. suppress all superfluous output.",
    )(function)


def implicit_configuration_option(function):
    def callback(context: click.Context, parameter: click.Parameter, value: Any):
        if value:
            with open(value, "rt") as file:
                contents = yaml.load(file, Loader=yaml.CLoader)
            context.obj = Configuration.parse_obj(contents)
        return value

    return click.option(
        "--config",
        default=None,
        type=click.types.Path(exists=True, file_okay=True, dir_okay=False),
        callback=callback,
        expose_value=False,  # Must be False!
        is_eager=True,  # Must be True!
        help="Path to the yaml configuration file.",
    )(function)


def implicit_debug_option(function):
    def callback(context: click.Context, parameter: click.Parameter, value: Any):
        state = context.ensure_object(AppState)
        state.debug = value

        log_format = "%(filename)s: %(message)s"
        if state.debug == 1:
            logging.basicConfig(
                format=log_format, stream=sys.stdout, level=logging.INFO
            )
        elif state.debug >= 1:
            logging.basicConfig(
                format=log_format, stream=sys.stdout, level=logging.DEBUG
            )

        state.quiet = True if state.debug > 1 else state.quiet
        return value

    return click.option(
        "-d",
        "--debug",
        count=True,
        callback=callback,
        metavar="",
        expose_value=False,  # Must be False!
        help="Enable debugging logs. Can be repeated to increase log level",
    )(function)


# Root command
@click.group()
@click.decorators.version_option(prog_name="conda-local", version=__version__)
def app():
    """Synthesize local anaconda channels from upstream sources."""
    pass


# Sub-command: search
@app.command(short_help="Search an upstream channel for packages and report results.")
@click.argument(
    "requirements",
    nargs=-1,
    type=click.types.STRING,
    callback=check_configuration("requirements"),
    is_eager=False,
)
@channel_option
@click.option(
    "-t",
    "--target",
    default="",
    type=click.types.STRING,
    callback=check_configuration("target"),
    is_eager=False,
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
@implicit_configuration_option
@implicit_quiet_option
@implicit_debug_option
@pass_state
@pydantic.validate_arguments
def search(
    state: AppState,
    requirements: List[str],
    channel: str,
    target: str,
    exclusions: List[str],
    disposables: List[str],
    subdirs: List[str],
    output: str,
):
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
    try:
        run_search(
            channel_url=channel,
            requirements=requirements,
            exclusions=exclusions,
            disposables=disposables,
            subdirs=subdirs,
            target_url=target,
            output=output,
            quiet=state.quiet,
        )
    except CondaReplicateException as exception:
        _process_application_exception(exception)


# Sub-command: update
@app.command(short_help="Update a local channel from an upstream channel.")
@click.argument(
    "requirements",
    nargs=-1,
    type=click.types.STRING,
    callback=check_configuration("requirements"),
    is_eager=False,
)
@click.option(
    "-t",
    "--target",
    required=True,
    type=click.types.STRING,
    callback=check_configuration("target"),
    is_eager=False,
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
@implicit_configuration_option
@implicit_quiet_option
@implicit_debug_option
@pass_state
@pydantic.validate_arguments
def update(
    state: AppState,
    requirements: List[str],
    channel: str,
    target: str,
    exclusions: List[str],
    disposables: List[str],
    subdirs: List[str],
):
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
    try:
        run_update(
            channel_url=channel,
            requirements=requirements,
            exclusions=exclusions,
            disposables=disposables,
            subdirs=subdirs,
            target_url=target,
            quiet=state.quiet,
        )
    except CondaReplicateException as exception:
        _process_application_exception(exception)


# Sub-command: patch
@app.command(short_help="Create a patch from an upstream channel.")
@click.argument(
    "requirements",
    nargs=-1,
    type=click.types.STRING,
    callback=check_configuration("requirements"),
    is_eager=False,
)
@click.option(
    "-t",
    "--target",
    default="",
    type=click.types.STRING,
    callback=check_configuration("target"),
    is_eager=False,
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
@implicit_configuration_option
@implicit_quiet_option
@implicit_debug_option
@pass_state
@pydantic.validate_arguments
def patch(
    state: AppState,
    requirements: List[str],
    target: str,
    name: str,
    parent: str,
    channel: str,
    exclusions: List[str],
    disposables: List[str],
    subdirs: List[str],
):
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
    try:
        run_patch(
            channel_url=channel,
            requirements=requirements,
            exclusions=exclusions,
            disposables=disposables,
            subdirs=subdirs,
            name=name,
            parent=parent,
            target_url=target,
            quiet=state.quiet,
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
@implicit_quiet_option
@implicit_debug_option
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
@implicit_quiet_option
@implicit_debug_option
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
