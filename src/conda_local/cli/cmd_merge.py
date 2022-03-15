from pathlib import Path

import click

from conda_local import api
from conda_local.cli import app


@app.command()
@click.argument(
    "target", nargs=1, type=click.Path(exists=False, file_okay=False, path_type=Path)
)
@click.argument(
    "patch", nargs=1, type=click.Path(exists=False, file_okay=False, path_type=Path)
)
@click.option(
    "--silent", is_flag=True, help="Do not show progress",
)
def merge(target, patch, silent):
    api.merge(target, patch, silent=silent)
    click.echo("Merge complete")
