from pathlib import Path

import click

from conda_local import api


@click.command()
@click.argument(
    "patch", nargs=1, type=click.Path(exists=False, file_okay=False, path_type=Path)
)
@click.argument(
    "target", nargs=1, type=click.Path(exists=False, file_okay=False, path_type=Path)
)
@click.option(
    "--silent", is_flag=True, help="Do not show progress",
)
def merge(patch, target, silent):
    """Merges a PATCH directory with a local TARGET anaconda directory."""
    api.merge(target, patch, silent=silent)
