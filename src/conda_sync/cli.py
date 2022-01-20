import click


@click.command()
@click.argument("specs", nargs=-1, type=str)
@click.option(
    "-c",
    "--channel",
    nargs=1,
    type=str,
    default="conda-forge",
    help="Canonical name or URI of the anaconda channel.",
)
@click.option(
    "-p",
    "--platform",
    type=str,
    multiple=True,
    help="Platforms or subdirs (noarch included by default).",
)
@click.option(
    "-t",
    "--target",
    type=click.Path(exists=False, file_okay=False),
    default=None,
    help="Local channel to be synced.",
)
@click.option(
    "--download",
    type=click.Path(exists=False, file_okay=False),
    default=None,
    help="Temporary download location.",
)
@click.option(
    "--exclude-noarch", is_flag=True, help="Exclude noarch packages.",
)
def app(specs, channel, platform, target, download, exclude_noarch):
    print(specs)
    print(channel)
    print(platform)
    print(target)
    print(download)
    print(exclude_noarch)
