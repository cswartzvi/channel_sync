import click

from conda_local.cli.commands import fetch, index, merge, query, sync


@click.group()
def app():
    """Manage local, potentially air-gapped, mirrored anaconda channels."""
    pass


app.add_command(query)
app.add_command(fetch)
app.add_command(sync)
app.add_command(index)
app.add_command(merge)
