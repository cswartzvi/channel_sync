import datetime
from pathlib import Path

import click

from conda_local import api
from conda_local.cli import app


@app.command()
@click.argument(
    "local", nargs=1, type=click.Path(exists=False, file_okay=False, path_type=Path),
)
@click.argument("upstream", nargs=1, type=str)
@click.argument("specs", nargs=-1, type=str)
@click.option(
    "-s",
    "--subdir",
    "subdirs",
    type=str,
    multiple=True,
    help="Platforms sub-directories to sync (defaults to current platform).",
)
@click.option(
    "--patch/--no-patch",
    default=False,
    help="Determines if packages should be downloaded to a separate directory.",
)
@click.option(
    "--patch-folder", default="", help="Override location for patch directory",
)
@click.option(
    "--silent", is_flag=True, default=False, help="Do not show progress",
)
def sync(local, upstream, specs, subdirs, patch, patch_folder, silent):

    if patch:
        if patch_folder:
            patch_folder = Path(patch_folder)
        else:
            now = datetime.datetime.now()
            patch_folder = Path(f"patch_{now.strftime('%Y%m%d_%H%M%S')}")

    api.sync(
        local=local,
        upstream=upstream,
        specs=specs,
        subdirs=subdirs,
        patch=patch_folder,
        silent=silent,
    )

    if patch:
        click.echo(f"Patch created: {patch_folder.resolve()}")
    else:
        click.echo("Sync complete")
