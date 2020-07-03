import collections
import datetime
import itertools
import pathlib
import yaml
from typing import Dict, List

import click

from isoconda.models import RepoData
import isoconda.processing as processing


@click.command()
@click.argument('config')
def update(config: str):
    """Generate a patch for a isolated Anaconda environment."""

    # Note: currently unknown configuration keys are ignored, but allowed.
    data = yaml.load(open(config, 'rt'), Loader=yaml.CLoader)
    subdirs = data.get('subdirs')
    local = data.get('local', None)
    versions = data.get('python_versions', [])
    patches = data.get('patches')
    print(f"Sub-directories:{subdirs}")
    print(f"Python version:{versions}")
    print(f"Reference Directory: {local}")

    local_repos: List[RepoData] = []
    if local is not None:
        local_repos = list(processing.fetch_local_repos(local, subdirs))

    now = datetime.datetime.now()
    patch = pathlib.Path(patches) / f'patch_{now.strftime("%Y%m%d_%H%M%S")}'
    patch.mkdir(parents=True, exist_ok=False)
    print(f"Patch file: {patch.absolute()}")

    channel_repos: Dict[str, List[RepoData]] = collections.defaultdict(list)
    for channeldata in data['channels']:
        url = channeldata.get('url')
        include = channeldata.get('include', [])
        exclude = channeldata.get('exclude', [])

        print(f"\nReading channel {url}")
        print(f"Include: {'Yes' if include else 'No'}")
        print(f"Exclude: {'Yes' if exclude else 'No'}")

        # Selected repositories need to be filtered prior to examining differences.
        original = processing.fetch_online_repos(url, subdirs)
        filtered = list(processing.filter_repos(original, include, exclude, versions))

        # If local repositories were defined, only include packages from
        # the cloud repository that local repos do not already contain.
        for local_repo in local_repos:
            for index, repo in enumerate(filtered):  # filtered must be indexedable
                if local_repo.subdir == repo.subdir:
                    filtered[index] = repo.difference(local_repo)
        channel_repos[url].extend(filtered)

    # Packages should be downloaded in groups of channels and repos.
    for channel, repos in channel_repos.items():
        print(f"\nDownloading from {channel}")
        for repo in repos:
            packages = list(itertools.chain.from_iterable(repo.values()))
            destination = pathlib.Path(patch) / repo.subdir
            processing.download_packages(channel, packages, destination)


if __name__ == '__main__':
    update()
