import click
from rich.console import Console

from conda_local.cli.options import (
    CONTEXT_SETTINGS,
    AppState,
    test_options,
    configuration_option,
    output_option,
    pass_state,
    patch_options,
    quiet_option,
    common_search_options,
    specifications_argument,
    update_options,
)
from conda_local.models.channel import (
    LocalCondaContainer
)
from conda_local.output import print_output
from conda_local.progress import iterate_progress, start_status
from conda_local.resolve import resolve_packages


@click.command(
    short_help="Search an anaconda channel for packages",
    context_settings=CONTEXT_SETTINGS,
)
@specifications_argument
@test_options
@common_search_options
@output_option
@configuration_option
@quiet_option
@pass_state
def test(state: AppState):
    """Search for packages and dependencies within an anaconda channel based on
    SPECIFICATIONS.

    \b
    Specifications are constructed using the anaconda match specification query syntax:
    https://docs.conda.io/projects/conda-build/en/latest/resources/package-spec.html#package-match-specifications
    """
    console = Console(quiet=state.quiet, color_system="windows")

    with start_status(f"Searching [bold cyan]{state.channel.name}", console=console):
        resolved = resolve_packages(
            channel=state.channel,
            subdirs=state.subdirs,
            requirements=state.requirements,
            constraints=state.constraints,
            disposables=state.disposables,
            reference=state.target,
            latest=state.latest,
            validate=state.validate,
        )
    print_output(state.output, resolved)


@click.command(
    short_help="Fetch packages from an anaconda channel",
    context_settings=CONTEXT_SETTINGS,
)
@specifications_argument
@test_options
@common_search_options
@patch_options
@quiet_option
@configuration_option
@pass_state
def patch(state: AppState):
    """Fetch packages and dependencies from an anaconda channel based on SPECIFICATIONS.

    \b
    Specifications are constructed using the anaconda match specification query syntax:
    https://docs.conda.io/projects/conda-build/en/latest/resources/package-spec.html#package-match-specifications
    """
    console = Console(quiet=state.quiet, color_system="windows")

    with start_status(f"Searching [bold cyan]{state.channel.name}", console=console):
        resolved = resolve_packages(
            channel=state.channel,
            subdirs=state.subdirs,
            requirements=state.requirements,
            constraints=state.constraints,
            disposables=state.disposables,
            reference=state.target,
            latest=state.latest,
            validate=state.validate,
        )

    patch = LocalCondaContainer(state.patch_directory.resolve() / state.patch_name)

    message = "Downloading packages "
    for package in iterate_progress(resolved.to_add, message, console=console):
        patch.add_package(package)

    message = "Patching instructions"
    for subdir in iterate_progress(state.subdirs, message, console=console):
        instructions = state.channel.read_patch_instructions(subdir)
        instructions.update(remove=list(pkg.fn for pkg in resolved.to_remove))
        patch.write_instructions(subdir, instructions)

    with start_status("Creating patch generator", console=console):
        patch.write_patch_generator()

    console.print(f"Patch location: [bold cyan]{patch.path.resolve()}")
    if console.quiet:
        print(patch.path.resolve())


@click.command(
    short_help="Fetch packages from an anaconda channel",
    context_settings=CONTEXT_SETTINGS,
)
@specifications_argument
@update_options
@common_search_options
@quiet_option
@configuration_option
@pass_state
def update(state: AppState):
    """Update an anaconda channel based on SPECIFICATIONS from an upstream channel.

    \b
    Specifications are constructed using the anaconda match specification query syntax:
    https://docs.conda.io/projects/conda-build/en/latest/resources/package-spec.html#package-match-specifications
    """
    console = Console(quiet=state.quiet, color_system="windows")

    with start_status(f"Searching [bold cyan]{state.channel.name}", console=console):
        resolved = resolve_packages(
            channel=state.channel,
            subdirs=state.subdirs,
            requirements=state.requirements,
            constraints=state.constraints,
            disposables=state.disposables,
            reference=state.target,
            latest=state.latest,
            validate=state.validate,
        )

    patch = LocalCondaContainer(state.patch_directory.resolve() / state.target)

    message = "Downloading packages "
    for package in iterate_progress(resolved.to_add, message, console=console):
        patch.add_package(package)

    message = "Patching instructions"
    for subdir in iterate_progress(state.subdirs, message, console=console):
        instructions = state.channel.read_patch_instructions(subdir)
        instructions.update(remove=list(pkg.fn for pkg in resolved.to_remove))
        patch.write_instructions(subdir, instructions)

    with start_status("Creating patch generator", console=console):
        patch.write_patch_generator()

    console.print(f"Patch location: [bold cyan]{patch.path.resolve()}")
    if console.quiet:
        print(patch.path.resolve())
