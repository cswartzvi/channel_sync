import click

import conda_local.api as api
from conda_local.cli.options import (
    CONTEXT_SETTINGS,
    ApplicationState,
    channel_options,
    common_search_options,
    configuration_option,
    output_option,
    patch_options,
    quiet_option,
    requirements_argument,
    target_argument,
)
from conda_local.cli.state import pass_state
from conda_local.output import print_output


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
    """Search for packages and dependencies within an anaconda channel based on
    REQUIREMENTS.

    \b
    Requirements and all other specifications are constructed using the anaconda package query syntax:
    https://docs.conda.io/projects/conda-build/en/latest/resources/package-spec.html#package-match-specifications
    """  # noqa: E501
    results = api.query(
        state.channel,
        state.requirements,
        state.constraints,
        state.disposables,
        state.subdirs,
        state.reference,
        state.latest,
        state.validate_,
    )

    print_output(state.output, results)


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
    """Fetch packages and dependencies from an anaconda channel based on REQUIREMENTS.

    \b
    Specifications are constructed using the anaconda match specification query syntax:
    https://docs.conda.io/projects/conda-build/en/latest/resources/package-spec.html#package-match-specifications
    """  # noqa: E501
    api.fetch(
        channel=state.channel,
        requirements=state.requirements,
        directory=state.patch_directory,
        name=state.patch_name,
        constraints=state.constraints,
        disposables=state.disposables,
        subdirs=state.subdirs,
        reference=state.reference,
        latest=state.latest,
        validate=state.validate_,
        quiet=state.quiet,
    )


@click.command(
    short_help="Update a local anaconda channel from an upstream channel.",
    context_settings=CONTEXT_SETTINGS,
)
@target_argument
@requirements_argument
@channel_options
@common_search_options
@quiet_option
@configuration_option
@pass_state
def update(state: ApplicationState):
    """Update a local anaconda channel from an upstream channel based on REQUIREMENTS.

    \b
    Specifications are constructed using the anaconda match specification query syntax:
    https://docs.conda.io/projects/conda-build/en/latest/resources/package-spec.html#package-match-specifications
    """  # noqa: E501
    api.update(
        channel=state.channel,
        target=state.target,
        requirements=state.requirements,
        constraints=state.constraints,
        disposables=state.disposables,
        subdirs=state.subdirs,
        reference=state.reference,
        latest=state.latest,
        validate=state.validate_,
        quiet=state.quiet
    )