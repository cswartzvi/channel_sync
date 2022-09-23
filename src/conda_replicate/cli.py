import logging
import sys
from typing import TYPE_CHECKING, Any, Callable, Set

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
from conda_replicate.core import run_query
from conda_replicate.core import run_update

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

_DEFAULT_SUBDIRS = get_default_subdirs()
_KNOWN_SUBDIRS = get_known_subdirs()
_ALLOWED_SUBDIRS = [subdir for subdir in sorted(_KNOWN_SUBDIRS)]


class AppState(BaseSettings):
    """Persistent application state."""

    channel: str = "conda-forge"
    target: str = ""
    latest_versions: bool = False
    latest_builds: bool = False
    latest_roots: bool = False
    debug: bool = False
    quiet: bool = False
    requirements: Set[str] = Field(default_factory=set)
    exclusions: Set[str] = Field(default_factory=set)
    disposables: Set[str] = Field(default_factory=set)
    subdirs: Set[str] = Field(default_factory=set)


pass_state = click.make_pass_decorator(AppState, ensure=True)


class Configuration(BaseSettings):
    """The current state of configuration file settings."""

    channel: str = ""
    target: str = ""
    requirements: Set[str] = Field(default_factory=set)
    exclusions: Set[str] = Field(default_factory=set)
    disposables: Set[str] = Field(default_factory=set)
    subdirs: Set[str] = Field(default_factory=set)
    latest_versions: bool = False
    latest_builds: bool = False
    latest_roots: bool = False
    quiet: bool = False


def channel_option(function: Callable):
    """Decorator for the `channel` option. Not exposed to the underlying command."""

    def callback(context: click.Context, parameter: click.Parameter, value: Any):
        state = context.ensure_object(AppState)
        if value:
            state.channel = value
        return state.channel

    return click.option(
        "-c",
        "--channel",
        "channel",
        type=click.types.STRING,
        callback=callback,
        show_default=True,
        expose_value=False,  # Must be False
        is_eager=False,  # Must be False
        help=(
            "Upstream anaconda channel. Can be specified using the canonical channel "
            "name on anaconda.org (conda-forge), a fully qualified URL "
            "(https://conda.anaconda.org/conda-forge/), or a local directory path."
        ),
    )(function)


def configuration_option(function):
    """Decorator for the `config` option. Not exposed to the underlying command."""

    def callback(context: click.Context, parameter: click.Parameter, value: Any):
        state = context.ensure_object(AppState)
        if value:
            with open(value, "rt") as file:
                contents = yaml.load(file, Loader=yaml.CLoader)
                configuration = Configuration.parse_obj(contents)

            for name in configuration.__fields_set__:
                setattr(state, name, getattr(configuration, name))
        return value

    return click.option(
        "--config",
        default=None,
        type=click.types.Path(exists=True, file_okay=True, dir_okay=False),
        callback=callback,
        expose_value=False,  # Must be False
        is_eager=True,  # Must be True
        help="Path to the yaml configuration file.",
    )(function)


def debug_option(function: Callable):
    """
    Decorator for the `quiet` command line option.  Not exposed underlying command.

    The `debug` option prints debugging information to stdout. Should force the
    quiet command to a matching value.
    """

    def callback(context: click.Context, parameter: click.Parameter, value: Any):
        state = context.ensure_object(AppState)
        if value is not None:
            state.debug = value
        if state.debug:
            logging.basicConfig(
                format="%(filename)s: %(message)s",
                stream=sys.stdout,
                level=logging.DEBUG,
            )
            state.quiet = True  # no animation / progress in debug mode
        return state.debug

    return click.option(
        "-d",
        "--debug",
        is_flag=True,
        default=None,  # Must be None
        callback=callback,
        expose_value=False,  # Must be False
        is_eager=False,  # Must be False
        help="Enable debugging output. Automatically enters quiet mode.",
    )(function)


def exclusions_option(function: Callable):
    """Decorator for the `exclude` option. Not exposed to the underlying command.

    Options specified on the command line are added to 'exclusions` list in the
    configuration file.
    """

    def callback(context: click.Context, parameter: click.Parameter, value: Any):
        state = context.ensure_object(AppState)
        if value:
            state.exclusions.update(value)
        return state.exclusions

    return click.option(
        "--exclude",
        "exclusions",
        multiple=True,
        type=click.types.STRING,
        callback=callback,
        expose_value=False,  # Must be False
        is_eager=False,  # Must be False
        help=(
            "Packages excluded from the search process. Specified using the anaconda "
            "package query syntax. Multiple options may be passed at one time. "
        ),
    )(function)


def disposables_option(function: Callable):
    """Decorator for the `dispose` option. Not exposed to the underlying command.

    Options specified on the command line are added to 'disposables` list in the
    configuration file.
    """

    def callback(context: click.Context, parameter: click.Parameter, value: Any):
        state = context.ensure_object(AppState)
        if value:
            state.disposables.update(value)
        return state.disposables

    return click.option(
        "--dispose",
        "disposables",
        multiple=True,
        type=click.types.STRING,
        callback=callback,
        expose_value=False,  # Must be False
        is_eager=False,  # Must be False
        help=(
            "Packages that are used in the search process but not included in the "
            "final results. Specified using the anaconda package query syntax. "
            "Multiple options may be passed at one time. "
        ),
    )(function)


def latest_builds_option(function: Callable):
    """Decorator for the `latest-version` option. Not exposed to the underlying command."""

    def callback(context: click.Context, parameter: click.Parameter, value: Any):
        state = context.ensure_object(AppState)
        if value is not None:
            state.latest_builds = value
        return state.latest_builds

    return click.option(
        "--latest-builds",
        is_flag=True,
        default=None,  # Must be None
        callback=callback,
        expose_value=False,  # Must be False
        is_eager=False,  # Must be False
        help=(
            "Force latest packages. Only returns the packages of the latest version "
            "for each of the requirements. Note that there may be multiple builds for "
            "each version of a package."
        ),
    )(function)


def latest_versions_option(function: Callable):
    """Decorator for the `latest` option. Not exposed to the underlying command."""

    def callback(context: click.Context, parameter: click.Parameter, value: Any):
        state = context.ensure_object(AppState)
        if value is not None:
            state.latest_versions = value
        return state.latest_versions

    return click.option(
        "--latest-version",
        is_flag=True,
        default=None,  # Must be None
        callback=callback,
        expose_value=False,  # Must be False
        is_eager=False,  # Must be False
        help=(
            "Force latest packages. Only returns the packages of the latest version "
            "for each of the requirements. Note that there may be multiple builds for "
            "each version of a package."
        ),
    )(function)


def quiet_option(function: Callable):
    """Decorator for the `quiet` option. Not exposed to the underlying command."""

    def callback(context: click.Context, parameter: click.Parameter, value: Any):
        state = context.ensure_object(AppState)
        if value is not None:
            state.quiet = value
        if state.debug:
            state.quiet = False
        return state.quiet

    return click.option(
        "--quiet",
        is_flag=True,
        default=None,  # Must be None
        callback=callback,
        expose_value=False,  # Must be False
        is_eager=False,  # Must be False
        help="Quite mode. Suppresses all animations and status related output.",
    )(function)


def requirements_argument(function: Callable):
    def callback(context: click.Context, parameter: click.Parameter, value: Any):
        state = context.ensure_object(AppState)
        if value:
            state.requirements.update(value)
        if not state.requirements:
            raise click.BadParameter("Missing option")
        return state.requirements

    return click.argument(
        "requirements",
        nargs=-1,
        type=click.types.STRING,
        callback=callback,
        is_eager=False,  # Must be False
        expose_value=False,  # Must be False
    )(function)


def subdirs_option(function: Callable):
    """Decorator for the `subdirs` option. Not exposed to the underlying command.

    Options specified on the command line are added to 'subdirs` list in the
    configuration file.
    """

    def callback(context: click.Context, parameter: click.Parameter, value: Any):
        state = context.ensure_object(AppState)
        if value:
            state.subdirs.update(value)
        return state.subdirs

    return click.option(
        "--subdir",
        "subdirs",
        multiple=True,
        type=click.types.Choice(_KNOWN_SUBDIRS),
        callback=callback,
        default=_DEFAULT_SUBDIRS,
        metavar="SUBDIR",
        show_default=True,
        expose_value=False,  # Must be False
        is_eager=False,  # Must be False
        help=(
            "Selected platform sub-directories. Multiple options may be passed at "
            f"one time. Allowed values: {{{', '.join(_ALLOWED_SUBDIRS)}}}."
        ),
    )(function)


def target_callback(context: click.Context, parameter: click.Parameter, value: Any):
    """Callback function for `target` options."""
    state = context.ensure_object(AppState)
    if value:
        state.target = value
    return state.target


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
    try:
        run_query(
            channel_url=state.channel,
            requirements=sorted(state.requirements),
            exclusions=sorted(state.exclusions),
            disposables=sorted(state.disposables),
            subdirs=sorted(state.subdirs),
            target_url=state.target,
            output=output,
            quiet=state.quiet,
            latest=state.latest_versions,
        )
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

    try:
        run_update(
            channel_url=state.channel,
            requirements=sorted(state.requirements),
            exclusions=sorted(state.exclusions),
            disposables=sorted(state.disposables),
            subdirs=sorted(state.subdirs),
            target_url=state.target,
            quiet=state.quiet,
            latest=state.latest_versions,
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
