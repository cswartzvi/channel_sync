import logging

import click

LOGGER = logging.Logger(__name__)


@click.group()
@click.option("-v", "--verbose", count=True, default=0)
def app(verbose):
    """Manage local or air-gapped anaconda channels."""
    if verbose > 0:
        LOGGER.setLevel(logging.INFO)
    if verbose > 1:
        LOGGER.setLevel(logging.DEBUG)


from conda_local.cli import cmd_diff, cmd_merge, cmd_sync, cmd_verify  # noqa
