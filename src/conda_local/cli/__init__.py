import logging

import click

from conda_local.cli import cmd_merge, cmd_patch, cmd_sync

LOGGER = logging.Logger(__name__)


@click.group()
@click.option("-v", "--verbose", count=True, default=0)
def app(verbose):
    """Manage local, potentially air-gapped, anaconda channels."""
    if verbose >= 1:
        logging.basicConfig(level=logging.DEBUG)
    elif verbose == 1:
        logging.basicConfig(level=logging.INFO)


app.add_command(cmd_merge.merge)
app.add_command(cmd_patch.patch)
app.add_command(cmd_sync.sync)
