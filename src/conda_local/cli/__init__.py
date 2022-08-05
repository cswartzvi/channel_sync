import click

# from conda_local.commands.fetch import fetch
from conda_local.cli.commands import fetch, search

# from conda_local.cli.search import search


@click.group()
def app():
    pass


app.add_command(search)
app.add_command(fetch)
