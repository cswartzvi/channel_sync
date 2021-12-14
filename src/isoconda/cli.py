import typing
import click
from itertools import chain
from urllib.parse import urljoin

from isoconda.packages import solve
from isoconda.repo import fetch_records, get_repodata_urls
from isoconda.specs import get_specs


@click.group()
def cli():
    pass


@cli.command()
@click.argument("channel", nargs=1, type=str)
@click.argument("specs", nargs=-1)
@click.option("-p", "--platforms", type=str, default=None, multiple=True)
def search(channel, specs, platforms):
    """Search CHANNEL for package records that satisfy the given match SPECS."""
    if platforms is None:
        platforms = []
    platforms += ("noarch",)

    urls = list(get_repodata_urls(channel, platforms))
    packages = chain.from_iterable(fetch_records(url) for url in urls)
    spec_objs = list(get_specs(specs))
    found_packages = solve(spec_objs, packages)
    for package in sorted(found_packages, key=lambda pkg: pkg.name):
        print(package.fn)
