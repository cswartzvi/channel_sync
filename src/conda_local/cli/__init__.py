from pathlib import Path
from tempfile import mkdtemp
from typing import Sequence

import click

from conda_local.packages import download_package
from conda_local.records import diff_records, query_records, read_records


@click.group()
@click.option("--debug", is_flag=True)
def app(debug):
    click.echo(f"Debug mode: {'ON' if debug else 'OFF'}")


@app.command()
@click.argument("specs", nargs=-1, type=str)
@click.option(
    "-c",
    "--channel",
    nargs=1,
    type=str,
    default="conda-forge",
    help="Canonical name or URI of the anaconda channel.",
)
@click.option(
    "-p",
    "--platform",
    "platforms",
    type=str,
    multiple=True,
    help="Platforms or subdirs (noarch included by default).",
)
@click.option(
    "-t",
    "--target",
    type=click.Path(exists=False, file_okay=False, path_type=Path),
    default=None,
    help="Local channel to be synced.",
)
@click.option(
    "--download",
    type=click.Path(exists=False, file_okay=False, path_type=Path),
    default=None,
    help="Temporary download location.",
)
@click.option(
    "--exclude-noarch",
    is_flag=True,
    help="Exclude noarch packages.",
)
def sync(specs, channel, platforms, target, download, exclude_noarch):
    platforms = list(platforms)
    if not exclude_noarch:
        platforms.append("noarch")

    if not target.exists():
        pass
    else:
        records =


@app.command()
def diff():
    click.echo("running diff...")


@app.command()
def merge():
    click.echo("running merge...")


@app.command()
def verify():
    click.echo("running verify...")

