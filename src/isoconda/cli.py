import click

# from itertools import chain


@click.group()
def cli():
    pass


@cli.command()
@click.argument("channel", nargs=1, type=str)
@click.argument("specs", nargs=-1)
@click.option("-p", "--platforms", type=str, default=None, multiple=True)
def search(channel, specs, platforms):
    pass
