"""High-level api functions for conda-local."""

import shutil
from pathlib import Path
from typing import Iterable, Iterator, List, Optional, Set, Tuple, TypeVar, Union, cast

from tqdm import tqdm

from conda_local._typing import OneOrMoreStrings, PathOrString
from conda_local.deps import DependencyFinder
from conda_local.external import (
    PackageRecord,
    Spinner,
    UnavailableInvalidChannel,
    compare_records,
    download_package,
    download_patch,
    get_current_subdirs,
    iter_channels,
    update_index,
)
from conda_local.patch import read_patch_summary

# from conda_local.spinner import Spinner

T = TypeVar("T", covariant=True)


def diff(
    local: PathOrString,
    upstream: OneOrMoreStrings,
    specs: OneOrMoreStrings,
    subdirs: Optional[OneOrMoreStrings] = None,
) -> Tuple[Set[PackageRecord], Set[PackageRecord]]:
    """Computes the difference between local and upstream anaconda channels.

    Args:
        channels: One of more upstream anaconda channels.
        local: The location of the local anaconda channel.
        subdirs: One or more anaconda subdirs (platforms).
        specs: One or more anaconda match specification strings

    Returns:
        A tuple of packages that should be added to the local anaconda channel,
        and packages that should be removed from the local anaconda channel.
    """
    local = Path(local)
    upstream = _ensure_list(upstream)
    subdirs = _ensure_subdirs(subdirs)
    specs = _ensure_list(specs)

    try:
        local_records = iterate(local.resolve().as_uri(), subdirs)
    except UnavailableInvalidChannel:
        # TODO: check condition of local directory
        local_records = iter([])

    upstream_records = query(upstream, specs, subdirs=subdirs)
    removed, added = compare_records(local_records, upstream_records)

    return added, removed


def iterate(
    channels: OneOrMoreStrings, subdirs: Optional[OneOrMoreStrings] = None,
) -> Iterator[PackageRecord]:
    """Yields all the package records in a specified channels and subdirs.

    Args:
        channels: One of more upstream anaconda channels.
        subdirs: One or more anaconda subdirs (platforms).
    """
    channels = _ensure_list(channels)
    subdirs = _ensure_subdirs(subdirs)
    records = iter_channels(channels, subdirs)
    yield from records


def merge(
    local: PathOrString,
    patch: PathOrString,
    *,
    index: bool = True,
    progress: bool = False,
):
    """Merges a patch produced by conda_local with a local anaconda channel.

    Args:
        local: The location of the local anaconda channel.
        patch: The location of the conda_local patch directory.
        index: Determines if the local channel index should be updated.

    """
    patch = Path(patch)
    local = Path(local)
    summary = read_patch_summary(patch / "patch_summary.json")
    disable = not progress

    for added in tqdm(
        summary.added, desc="Adding packages", disable=disable, leave=False
    ):
        source = patch / added
        destination = local / added
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(source, destination)
    if progress:
        print("Adding packages:", "done")

    for removed in tqdm(
        summary.removed, desc="Removing packages", disable=disable, leave=False,
    ):
        path = local / removed
        path.unlink(missing_ok=True)
    if progress:
        print("Adding packages:", "done")

    if index:
        update_index(local, progress=progress, subdirs=[])

        if progress:
            print("Updating index:", "done")


def query(
    channels: OneOrMoreStrings,
    specs: OneOrMoreStrings,
    *,
    subdirs: Optional[OneOrMoreStrings] = None,
    graph_file: Optional[PathOrString] = None,
) -> Iterable[PackageRecord]:
    """Executes a query of anaconda match specifications against anaconda channels.

    Args:
        channels: One or more upstream anaconda channels.
        subdirs: One or more anaconda subdirs (platforms).
        specs: One or more anaconda match specification strings.
        graph_file: Optional save location of the query dependency graph.

    Returns:
        A iterable of resulting package records from the executed query.
    """
    channels = _ensure_list(channels)
    subdirs = _ensure_subdirs(subdirs)
    specs = _ensure_list(specs)
    finder = DependencyFinder(channels, subdirs)
    records, graph = finder.search(specs)
    if graph_file is not None:
        graph_file = Path(graph_file)
    return records


def sync(
    channels: OneOrMoreStrings,
    local: PathOrString,
    specs: OneOrMoreStrings,
    *,
    subdirs: Optional[OneOrMoreStrings] = None,
    index: bool = True,
    verify: bool = True,
    patch: PathOrString = "",
    progress: bool = False,
) -> None:
    """Syncs a local anaconda channel with upstream anaconda channels.

    Args:
        channels: One or more upstream anaconda channels.
        local: The location of the local anaconda channel.
        subdirs: One or more anaconda subdirs (platforms).
        specs: One or more anaconda match specification strings
        index: Determines if the local channel index should be updated.
        verify: Determines if downloaded packages should be verified.
        patch: The location of the patch folder.
        progress: Determines if a progress bar should be shown.
    """
    channels = _ensure_list(channels)
    local = _ensure_local_channel(local)
    subdirs = _ensure_subdirs(subdirs)
    print(subdirs)

    destination = local if not patch else Path(patch)
    destination.mkdir(parents=True, exist_ok=True)

    with Spinner("Reading upstream channels", enabled=progress):
        added_records, _ = diff(local, channels, subdirs, specs)

    for subdir in tqdm(
        subdirs, desc="Downloading patches", disable=not progress, leave=False
    ):
        download_patch(channels, destination, subdir)
    if progress:
        print("Downloading patches:", "done")

    records = sorted(added_records, key=lambda rec: rec.fn)
    for record in tqdm(
        records, desc="Downloading packages", disable=not progress, leave=False
    ):
        download_package(record, destination, verify)
    if progress:
        print("Downloading packages:", "done")

    if index and not patch:
        update_index(local, progress=progress, subdirs=subdirs)

        if progress:
            print("Updating index:", "done")


def _ensure_list(items: Union[T, Iterable[T]]) -> List[T]:
    """Ensures that a specified variable is list of elements."""
    if not isinstance(items, Iterable):
        return cast(List[T], [items])
    if isinstance(items, str):
        return cast(List[T], [items])
    return cast(List[T], list(items))


def _ensure_local_channel(path: PathOrString) -> Path:
    path = Path(path)
    noarch_repo = path / "noarch" / "repodata.json"
    noarch_repo.parent.mkdir(exist_ok=True, parents=True)
    noarch_repo.touch(exist_ok=True)
    return path


def _ensure_subdirs(subdirs: Optional[OneOrMoreStrings]) -> List[str]:
    if subdirs is None:
        return get_current_subdirs()
    return _ensure_list(subdirs)
