import logging
from typing import Iterable, Iterator, List, Optional

from conda_replicate.adapters.channel import CondaChannel
from conda_replicate.adapters.package import CondaPackage
from conda_replicate.adapters.subdir import get_default_subdirs
from conda_replicate.resolver.graph import create_dependency_graph
from conda_replicate.resolver.graph import extract_dependency_graph_packages
from conda_replicate.resolver.query import ExclusionFilter
from conda_replicate.resolver.query import InclusionFilter
from conda_replicate.resolver.query import LatestVersionFilter
from conda_replicate.resolver.query import PackageFilter
from conda_replicate.resolver.query import PackageQuery

logger = logging.getLogger(__name__)

Specs = Iterable[str]


def find_packages(
    channel: CondaChannel,
    requirements: Specs,
    exclusions: Optional[Specs] = None,
    disposables: Optional[Specs] = None,
    subdirs: Optional[Specs] = None,
    latest_versions: bool = False,
    latest_builds: bool = False,
    latest_roots: bool = False,
) -> Iterator[CondaPackage]:
    subdirs = get_default_subdirs() if subdirs is None else tuple(subdirs)

    filters: List[PackageFilter] = []
    if requirements:
        filters.append(InclusionFilter(requirements))

    if exclusions:
        filters.append(ExclusionFilter(exclusions))

    if latest_versions:
        if latest_roots:
            filters.append(LatestVersionFilter())
        else:
            filters.append(LatestVersionFilter(requirements))

    if latest_builds:
        if latest_roots:
            filters.append(LatestVersionFilter())
        else:
            filters.append(LatestVersionFilter(requirements))

    query = PackageQuery(channel, subdirs, *filters)
    graph = create_dependency_graph(requirements, query)
    packages = extract_dependency_graph_packages(graph)

    if disposables:
        filter_ = ExclusionFilter(disposables)
        packages = filter_(packages)

    yield from packages
