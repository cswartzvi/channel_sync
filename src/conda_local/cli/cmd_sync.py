import datetime
from pathlib import Path

import click

from conda_local import api
from conda_local.cli import app


@app.command()
@click.argument("specs", nargs=-1, type=str)
@click.option(
    "-c",
    "--channel",
    "channels",
    multiple=True,
    required=True,
    type=str,
    help="Upstream anaconda channel canonical names or URI.",
)
@click.option(
    "-s",
    "--subdir",
    "subdirs",
    type=str,
    multiple=True,
    help="Upstream subdirs (platforms) to sync (noarch included by default).",
)
@click.option(
    "-t",
    "--target",
    required=True,
    type=click.Path(exists=False, file_okay=False, path_type=Path),
    help="Local anaconda channel to be synced.",
)
@click.option(
    "--patch/--no-patch",
    default=False,
    help="Determines if packages should be downloaded to a separate directory.",
)
@click.option(
    "--noarch/--no-noarch",
    default=True,
    help="Determines if the 'noarch' subdir should be included.",
)
@click.option(
    "--index/--no-index",
    default=True,
    help="Determines if the index of the download packages should be updated.",
)
@click.option(
    "--verify/--no-verify",
    default=True,
    help="Determins if download packages should be verified.",
)
@click.option(
    "--patch-folder", default="", help="Override location for patch directory",
)
def sync(specs, channels, subdirs, target, patch, noarch, index, verify, patch_folder):
    if noarch:
        if "noarch" not in subdirs:
            subdirs += ("noarch",)

    if patch:
        if patch_folder:
            patch_folder = Path(patch_folder)
        else:
            now = datetime.datetime.now()
            patch_folder = Path(f"patch_{now.strftime('%Y%m%d_%H%M%S')}")

    api.sync(
        channels,
        target,
        subdirs,
        specs,
        index=index,
        verify=verify,
        patch=patch_folder,
        progress=True,
    )

    if patch:
        click.echo(f"Patch created: {patch_folder.resolve()}")
    else:
        click.echo("Synchronization complete!")
