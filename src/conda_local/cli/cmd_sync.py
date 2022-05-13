import json
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
    help="Platforms sub-directories (defaults to current platform).",
)
@click.option(
    "--silent", is_flag=True, default=False, help="Do not show progress",
)
@click.option(
    "--keep", is_flag=True, default=False, help="Only add packages, do not remove",
)
@click.option(
    "--dry-run", is_flag=True, default=False, help="Show all packages to synced",
)
def sync(target, upstream, specs, subdirs, silent, keep, latest, dry_run):
    """Syncs a TARGET anaconda channel to an UPSTREAM anaconda channel with packages
    and recursive dependencies defined in anaconda match specification strings (SPECS).
    """

    silent = True if dry_run else silent

    results = api.synchronize(
        target=target,
        upstream=upstream,
        specs=specs,
        subdirs=subdirs,
        silent=silent,
        keep=keep,
        dry_run=dry_run,
    )

    if dry_run:
        summary = {
            "added": sorted(rec.fn for rec in results["added"]),
            "removed": sorted(rec.fn for rec in results["removed"]),
        }
        print(json.dumps(summary, indent=4))
