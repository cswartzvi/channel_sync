"""Adapters and centralized access point for the `conda` public APIs."""

from typing import Iterable, Iterator, Union

from conda.api import SubdirData
from conda.exports import PackageRecord


class ChannelData:
    """High-level management and usage of an anaconda channel.

    Args:
        channel: The target anaconda channel url or identifier, e.g.:
            * "https://repo.anaconda.com/pkgs/main/linux-64"
            * "conda-forge/linux-64"
            * "file:///path/to/local/channel"
        platforms: The selected platforms within the anaconda channel.
    """

    def __init__(self, channel: str, platforms: Union[str, Iterable[str]]) -> None:
        if not channel.endswith("/"):
            channel += "/"
        if isinstance(platforms, str):
            platforms = [platforms]
        self._subdirs = [SubdirData(channel + platform) for platform in platforms]

    def iter_records(self) -> Iterator[PackageRecord]:
        """Yields all package records contained in the anaconda channel."""
        for subdir in self._subdirs:
            yield from subdir.iter_records()

    def query(self, specs: Union[str, Iterable[str]]) -> Iterator[PackageRecord]:
        """Run a package record query against the anaconda channel.

        Args:
            specs: The package match specifications used within the query. Read more:
                https://docs.conda.io/projects/conda/en/latest/user-guide/concepts/pkg-specs.html#package-match-specifications  # noqa

        Returns:
            A set of all packages satisfying the package match specification.
        """
        if isinstance(specs, str):
            specs = [specs]
        for spec in specs:
            for subdir in self._subdirs:
                yield from subdir.query(spec)

    def reload(self) -> None:
        """Reload cached repodata.json files for subdirs."""
        for subdir in self._subdirs:
            subdir.reload()
