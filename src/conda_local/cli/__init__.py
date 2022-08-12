import click

from conda_local.cli.commands import patch
from conda_local.cli.commands import index
from conda_local.cli.commands import merge
from conda_local.cli.commands import search
from conda_local.cli.commands import sync


@click.group()
def app():
    """Manage local, potentially air-gapped, mirrored anaconda channels."""
    pass


app.add_command(search)
app.add_command(patch)
app.add_command(sync)
app.add_command(index)
app.add_command(merge)
