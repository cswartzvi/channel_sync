import click

from conda_local.cli import app


@app.command()
def merge():
    click.echo("running merge...")
