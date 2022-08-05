from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

import click
import yaml
from click_option_group import optgroup

from conda_local.models import get_default_subdirs
from conda_local.models.channel import CondaChannel
from conda_local.models.spec import CondaSpecification

CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"], "max_content_width": 150}


def _default_patch_name() -> str:
    now = datetime.datetime.now()
    name = f"patch_{now.strftime('%Y%m%d_%H%M%S')}"
    return name


@dataclass
class AppState:
    channel: CondaChannel = CondaChannel("conda-forge")
    reference: Optional[CondaChannel] = None
    requirements: List[CondaSpecification] = field(default_factory=list)
    constraints: List[CondaSpecification] = field(default_factory=list)
    disposables: List[CondaSpecification] = field(default_factory=list)
    subdirs: List[str] = field(default_factory=get_default_subdirs)
    patch_name: str = field(default_factory=_default_patch_name)
    patch_directory: Path = field(default_factory=Path)
    latest: bool = True
    validate: bool = True
    output: str = "summary"
    quiet: bool = False

    @staticmethod
    def default_patch_name() -> str:
        now = datetime.datetime.now()
        name = f"patch_{now.strftime('%Y%m%d_%H%M%S')}"
        return name


pass_state = click.make_pass_decorator(AppState, ensure=True)


def configuration_option(f, option=click.option):
    def callback(context, parameter, value):
        if value:
            state = _get_context_state(context)
            with open(value, "rt") as file:
                data = yaml.load(file, Loader=yaml.CLoader)
                for key, values in data.items():
                    if key in ["channel", "reference"]:
                        setattr(state, key, CondaChannel(values))
                    elif key in ["requirements", "constraints", "disposables"]:
                        setattr(state, key, [CondaSpecification(val) for val in values])
                    elif hasattr(state, key):
                        setattr(state, key, values)
                    else:
                        raise ValueError(f"Unknown configuration option {key}")
                context.default_map = data
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


def specifications_argument(f):
    def callback(context, parameter, values):
        state = _get_context_state(context)
        if values:
            specs = [CondaSpecification(value) for value in values]
            state.requirements.extend(specs)
        return values

    return click.argument(
        "requirements",
        nargs=-1,
        callback=callback,
        expose_value=False,
        is_eager=False,
        type=click.types.STRING,
    )(f)


def channel_option(f, option=click.option):
    def callback(context, parameter, value):
        state = _get_context_state(context)
        if value:
            state.channel = CondaChannel(value)
        else:
            value = state.channel.url
        return value

    return option(
        "-c",
        "--channel",
        required=True,
        nargs=1,
        callback=callback,
        expose_value=False,
        is_eager=False,
        help="Source anaconda channel, used as the basis for all upstream operations.",
    )(f)


def target_option(f, option=click.option):
    def callback(context, parameter, value):
        state = _get_context_state(context)
        if value:
            state.reference = CondaChannel(value)
        return value

    return option(
        "--target",
        required=False,
        nargs=1,
        callback=callback,
        expose_value=False,
        is_eager=False,
        help=(
            "Target anaconda channel, forces all operations to be preformed relative "
            "this baseline."
        ),
    )(f)


def constraint_option(f, option=click.option):
    def callback(context, parameter, values):
        state = _get_context_state(context)
        if values:
            specs = [CondaSpecification(value) for value in values]
            state.constraints.extend(specs)
        return values

    return option(
        "--constraint",
        "constraints",
        multiple=True,
        type=click.types.STRING,
        callback=callback,
        expose_value=False,
        is_eager=False,
        help="Match specification for packages that constrain the search process.",
    )(f)


def disposable_option(f, option=click.option):
    def callback(context, parameter, values):
        state = _get_context_state(context)
        if values:
            specs = [CondaSpecification(value) for value in values]
            state.disposables.extend(specs)
        return values

    return option(
        "--disposable",
        "disposables",
        multiple=True,
        type=click.types.STRING,
        callback=callback,
        expose_value=False,
        is_eager=False,
        help=(
            "Match specification for packages that are disposed of after the search "
            "process."
        ),
    )(f)


def subdir_option(f, option=click.option):
    def callback(context, parameter, values):
        state = _get_context_state(context)
        if values:
            if set(state.subdirs) == set(get_default_subdirs()):
                state.subdirs = []
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
            "Selected platform sub-directories of the anaconda channel, defaults to "
            "current platform."
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
        help=("Limits the search process to only the latest build for a package."),
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
        help="Quite mode, suppresses all output.",
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
            directory = Path(value)
            directory.mkdir(exist_ok=True, parents=True)
            state.patch_directory = directory
        return value

    return option(
        "--directory",
        default=None,
        type=click.types.Path(dir_okay=True, path_type=Path),
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


def channel_options(f):
    option = optgroup.option
    group = optgroup.group("Channel configuration")

    # Reverse order
    f = subdir_option(f, option=option)
    f = target_option(f, option=option)
    f = channel_option(f, option=option)
    f = group(f)

    return f


def search_options(f):
    option = optgroup.option
    group = optgroup.group("Search Options")

    # Reverse order
    f = validate_option(f, option=option)
    f = latest_option(f, option=option)
    f = disposable_option(f, option=option)
    f = constraint_option(f, option=option)
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


def _get_context_state(context: click.Context) -> AppState:
    return context.ensure_object(AppState)
