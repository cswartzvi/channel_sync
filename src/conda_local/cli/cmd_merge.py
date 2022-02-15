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
def merge(target, patch):
    api.merge(target, patch, progress=True)
    click.echo("Merge complete!")
