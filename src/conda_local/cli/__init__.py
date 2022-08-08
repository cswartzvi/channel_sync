import click

from conda_local.cli.commands import fetch, query, update


@click.group()
def app():
    pass


app.add_command(query)
app.add_command(fetch)
app.add_command(update)
