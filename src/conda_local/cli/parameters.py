from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, List, Optional

import click
import yaml
from click_option_group import optgroup
from pydantic import BaseSettings, Field

from conda_local.models.channel import CondaChannel, LocalCondaContainer
from conda_local.models.specification import CondaSpecification

CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"], "max_content_width": 130}


@dataclass
class ApplicationState:
    channel: CondaChannel = field(default_factory=lambda: CondaChannel("conda-forge"))
    requirements: List[CondaSpecification] = field(default_factory=list)
    exclusions: List[CondaSpecification] = field(default_factory=list)
    disposables: List[CondaSpecification] = field(default_factory=list)
    target: Optional[LocalCondaContainer] = None
    source: Optional[LocalCondaContainer] = None
    destination: Optional[LocalCondaContainer] = None
    subdirs: List[str] = field(default_factory=list)
    patch_directory: str = ""
    patch_name: str = ""
    validate: bool = True
    latest: bool = True
    output: str = "summary"
    quiet: bool = False


class Configuration(BaseSettings):
    channel: str = ""
    requirements: List[str] = Field(default_factory=list)
    exclusions: List[str] = Field(default_factory=list)
    disposables: List[str] = Field(default_factory=list)
    subdirs: List[str] = Field(default_factory=list)
    target: Optional[Path] = None
    validate_: Optional[bool] = None
    latest: Optional[bool] = None


pass_state = click.make_pass_decorator(ApplicationState, ensure=True)


def configuration_option(f, option=click.option):
    def callback(context, parameter, value):
        if value:
            state = _get_context_state(context)
            with open(value, "rt") as file:
                contents = yaml.load(file, Loader=yaml.CLoader)
            config = Configuration.parse_obj(contents)

            if config.channel:
                state.channel = CondaChannel(config.channel)

            if config.target:
                path = config.target
                if not path.exists():
                    path = path.absolute()
                state.target = LocalCondaContainer(path)

            if config.requirements:
                state.requirements = _make_specs(config.requirements)

            if config.exclusions:
                state.exclusions = _make_specs(config.exclusions)

            if config.disposables:
                state.disposables = _make_specs(config.disposables)

            if config.subdirs:
                state.subdirs = list(config.subdirs)

            if config.validate_ is not None:
                state.validate = config.validate_

            if config.latest is not None:
                state.latest = config.latest

        return value

    return option(
        "--config",
        default=None,
        type=click.types.Path(exists=True, file_okay=True, dir_okay=False),
        callback=callback,
        expose_value=False,
        is_eager=True,
        help="Read command line arguments from a configuration yaml file.",
    )(f)


def requirements_argument(f):
    def callback(context, parameter, values):
        if values:
            specs = _make_specs(values)
            state = _get_context_state(context)
            state.requirements.extend(specs)
        return values

    return click.argument(
        "requirements",
        nargs=-1,
        type=click.types.STRING,
        callback=callback,
        expose_value=False,
        is_eager=False,
    )(f)


def target_argument(f):
    def callback(context, parameter, value):
        if value:
            path = Path(value)
            if not path.exists():
                path = path.absolute()
            target = LocalCondaContainer(path)
            state = _get_context_state(context)
            state.target = target
        return value

    return click.argument(
        "target",
        nargs=1,
        type=click.types.Path(dir_okay=True, resolve_path=True),
        callback=callback,
        expose_value=False,
        is_eager=False,
    )(f)


def target_option(f, option=click.option):
    def callback(context, parameter, value):
        if value:
            path = Path(value)
            if not path.exists():
                path = path.absolute()
            target = LocalCondaContainer(path)
            state = _get_context_state(context)
            state.target = target
        return value

    return option(
        "--target",
        required=False,
        nargs=1,
        type=click.types.STRING,
        callback=callback,
        expose_value=False,
        is_eager=False,
        help="Target anaconda channel, used as a baseline in the search process.",
    )(f)


def source_argument(f):
    def callback(context, parameter, value):
        if value:
            path = Path(value)
            source = LocalCondaContainer(path)
            state = _get_context_state(context)
            state.source = source
        return value

    return click.argument(
        "source",
        nargs=1,
        type=click.types.Path(exists=True, dir_okay=True),
        callback=callback,
        expose_value=False,
        is_eager=False,
    )(f)


def destination_argument(f):
    def callback(context, parameter, value):
        if value:
            path = Path(value)
            destination = LocalCondaContainer(path)
            state = _get_context_state(context)
            state.destination = destination
        return value

    return click.argument(
        "destination",
        nargs=1,
        type=click.types.Path(exists=True, dir_okay=True),
        callback=callback,
        expose_value=False,
        is_eager=False,
    )(f)


def channel_option(f, option=click.option):
    def callback(context, parameter, value):
        if value:
            channel = CondaChannel(value)
            state = _get_context_state(context)
            state.channel = channel
        return value

    return option(
        "-c",
        "--channel",
        nargs=1,
        type=click.types.STRING,
        callback=callback,
        expose_value=False,
        is_eager=False,
        help=(
            "Source anaconda channel, the upstream channel in the search process. "
            "[conda-forge]."
        ),
    )(f)


def constraint_option(f, option=click.option):
    def callback(context, parameter, values):
        if values:
            specs = _make_specs(values)
            state = _get_context_state(context)
            state.exclusions.extend(specs)
        return values

    return option(
        "--exclude",
        multiple=True,
        type=click.types.STRING,
        callback=callback,
        expose_value=False,
        is_eager=False,
        help=(
            "Specification for packages that are excluded from the search process "
            "(multiple allowed)."
        ),
    )(f)


def disposable_option(f, option=click.option):
    def callback(context, parameter, values):
        if values:
            specs = _make_specs(values)
            state = _get_context_state(context)
            state.disposables.extend(specs)
        return values

    return option(
        "--disposable",
        multiple=True,
        type=click.types.STRING,
        callback=callback,
        expose_value=False,
        is_eager=False,
        help=(
            "Specification for packages that are disposed of after the search "
            "process (multiple allowed)."
        ),
    )(f)


def subdir_option(f, option=click.option):
    def callback(context, parameter, values):
        if values:
            state = _get_context_state(context)
            state.subdirs.extend(values)
        return values

    return option(
        "--subdir",
        multiple=True,
        type=click.types.STRING,
        callback=callback,
        expose_value=False,
        is_eager=False,
        help=(
            "Selected platform sub-directories (Multiple allowed). [current platform]"
        ),
    )(f)


def latest_option(f, option=click.option):
    def callback(context, parameter, value):
        state = _get_context_state(context)
        state.latest = value
        return value

    return option(
        "--latest/--no-latest",
        is_flag=True,
        default=True,
        type=click.types.BOOL,
        callback=callback,
        expose_value=False,
        is_eager=False,
        help="Limits the search process to only the latest build number of a package.",
    )(f)


def validate_option(f, option=click.option):
    def callback(context, parameter, value):
        state = _get_context_state(context)
        state.validate = value
        return value

    return option(
        "--validate/--no-validate",
        is_flag=True,
        default=True,
        type=click.types.BOOL,
        callback=callback,
        expose_value=False,
        is_eager=False,
        help=(
            "Raises an error if all requirements are not satisfied during the search "
            "process."
        ),
    )(f)


def quiet_option(f, option=click.option):
    def callback(context, parameter, value):
        state = _get_context_state(context)
        state.quiet = value
        return value

    return option(
        "--quiet",
        is_flag=True,
        default=False,
        type=click.types.BOOL,
        callback=callback,
        expose_value=False,
        is_eager=False,
        help="Quite mode, suppress all output.",
    )(f)


def patch_name_option(f, option=click.option):
    def callback(context, parameter, value):
        state = _get_context_state(context)
        if value:
            state.patch_name = value
        return value

    return option(
        "--name",
        default=None,
        type=click.types.STRING,
        callback=callback,
        expose_value=False,
        is_eager=False,
        help="Name of the patch, defaults to 'patch_%Y%m%d_%H%M%S'",
    )(f)


def patch_directory_option(f, option=click.option):
    def callback(context, parameter, value):
        state = _get_context_state(context)
        if value:
            state.patch_directory = value
        return value

    return option(
        "--directory",
        default=None,
        type=click.types.Path(dir_okay=True),
        callback=callback,
        expose_value=False,
        is_eager=False,
        help="Parent directory where patches will be written.",
    )(f)


def output_option(f, option=click.option):
    def callback(context, parameter, value):
        state = _get_context_state(context)
        if value:
            state.output = value
        return value

    return option(
        "--output",
        type=click.types.Choice(["summary", "list", "json"]),
        callback=callback,
        expose_value=False,
        is_eager=False,
        help="Specifies the format of the output.",
    )(f)


def common_search_options(f):
    option = optgroup.option
    group = optgroup.group("Search Options")

    # Reverse order
    f = validate_option(f, option=option)
    f = latest_option(f, option=option)
    f = disposable_option(f, option=option)
    f = constraint_option(f, option=option)
    f = group(f)

    return f


def channel_options(f):
    option = optgroup.option
    group = optgroup.group("Channel configuration")

    # Reverse order
    f = subdir_option(f, option=option)
    f = target_option(f, option=option)
    f = channel_option(f, option=option)
    f = group(f)

    return f


def sync_options(f):
    option = optgroup.option
    group = optgroup.group("Channel configuration")

    # Reverse order
    f = subdir_option(f, option=option)
    f = target_option(f, option=option)
    f = channel_option(f, option=option)
    f = group(f)

    return f


def patch_options(f):
    option = optgroup.option
    group = optgroup.group("Patch Options")

    # Reverse order
    f = patch_directory_option(f, option=option)
    f = patch_name_option(f, option=option)
    f = group(f)

    return f


def _get_context_state(context: click.Context) -> ApplicationState:
    return context.ensure_object(ApplicationState)


def _make_specs(items: Iterable[str]) -> List[CondaSpecification]:
    specs: List[CondaSpecification] = []
    for item in items:
        spec = CondaSpecification(item)
        specs.append(spec)
    return specs
