import datetime
from pathlib import Path

import click

from conda_local import api


@click.command()
@click.argument(
    "target", nargs=1, type=click.Path(exists=False, file_okay=False, path_type=Path),
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
    "-f", "--folder", default="", help="Override location for patch directory",
)
@click.option(
    "--silent", is_flag=True, default=False, help="Do not show progress",
)
def patch(target, upstream, specs, subdirs, folder, silent):
    """Creates a patch folder that can be used to sync a TARGET anaconda channel to an
    UPSTREAM anaconda channel with packages and recursive dependencies defined in
    anaconda match specification strings (SPECS)."""

    if folder:
        folder = Path(folder)
    else:
        now = datetime.datetime.now()
        folder = Path(f"patch_{now.strftime('%Y%m%d_%H%M%S')}")

    api.synchronize(
        target=target,
        upstream=upstream,
        specs=specs,
        subdirs=subdirs,
        patch=folder,
        silent=silent,
    )

    click.echo(f"Patch created: {folder.resolve()}")
