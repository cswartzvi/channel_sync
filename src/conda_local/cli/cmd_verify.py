import click

from conda_local.cli import app


@app.command()
def verify():
    click.echo("running verify...")
