from __future__ import annotations

from pathlib import Path

import click
import yaml
from click_option_group import optgroup

from conda_local.cli.state import ApplicationState, ConfigurableState

CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"], "max_content_width": 150}


def configuration_option(f, option=click.option):
    def callback(context, parameter, value):
        if value:
            state = _get_context_state(context)
            with open(value, "rt") as file:
                contents = yaml.load(file, Loader=yaml.CLoader)
            configuration = ConfigurableState.parse_obj(contents)
            state.update(configuration)
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
        state = _get_context_state(context)
        if values:
            state.requirements.extend(values)
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
        state = _get_context_state(context)
        if value:
            state.target = value
        return value

    return click.argument(
        "target",
        nargs=1,
        type=click.types.STRING,
        callback=callback,
        expose_value=False,
        is_eager=False,
    )(f)


def channel_option(f, option=click.option):
    def callback(context, parameter, value):
        state = _get_context_state(context)
        if value:
            state.channel = value
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


def reference_option(f, option=click.option):
    def callback(context, parameter, value):
        state = _get_context_state(context)
        if value:
            state.reference = value
        return value

    return option(
        "--reference",
        required=False,
        nargs=1,
        type=click.types.STRING,
        callback=callback,
        expose_value=False,
        is_eager=False,
        help="Reference anaconda channel, used as a baseline in the search process.",
    )(f)


def constraint_option(f, option=click.option):
    def callback(context, parameter, values):
        state = _get_context_state(context)
        if values:
            state.constraints.extend(values)
        return values

    return option(
        "--constraint",
        "constraints",
        multiple=True,
        type=click.types.STRING,
        callback=callback,
        expose_value=False,
        is_eager=False,
        help=(
            "Specification for packages that constrain the search process "
            "(multiple allowed)."
        ),
    )(f)


def disposable_option(f, option=click.option):
    def callback(context, parameter, values):
        state = _get_context_state(context)
        if values:
            state.disposables.extend(values)
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
            "Specification for packages that are disposed of after the search "
            "process (multiple allowed)."
        ),
    )(f)


def subdir_option(f, option=click.option):
    def callback(context, parameter, values):
        state = _get_context_state(context)
        if values:
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
        state.validate_ = value
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
    f = reference_option(f, option=option)
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
