import click

from conda_local.cli import app


@app.command()
def diff():
    click.echo("running diff...")
