"""High-level api functions for conda-local."""

import shutil
from pathlib import Path
from typing import Iterable, Iterator, List, Optional, Set, Tuple, TypeVar, Union, cast

from tqdm import tqdm

from conda_local._typing import OneOrMorePackageRecords, OneOrMoreStrings, PathOrString
from conda_local.adapters import (
    ChannelData,
    PackageRecord,
    UnavailableInvalidChannel,
    download_package,
    update_index,
)
from conda_local.deps import DependencyFinder
from conda_local.patch import read_patch_summary, write_patch_summary
from conda_local.spinner import Spinner

T = TypeVar("T", covariant=True)


def diff(
    channels: OneOrMoreStrings,
    local: PathOrString,
    subdirs: OneOrMoreStrings,
    specs: OneOrMoreStrings,
) -> Tuple[Set[PackageRecord], Set[PackageRecord]]:
    """Computes the difference between upsteam and local anaconda channels.

    Args:
        channels: One of more upstream anaconda channels.
        local: The location of the local anaconda channel.
        subdirs: One or more anaconda subdirs (platforms).
        specs: One or more anaconda match specification strings

    Returns:
        A tuple of packages that should be added to the local anaconda channel,
        and packages that should be removed from the local anaconda channel.
    """
    channels = _ensure_list(channels)
    local = Path(local)
    subdirs = _ensure_list(subdirs)
    specs = _ensure_list(specs)

    try:
        local_records = set(iterate(local.resolve().as_uri(), subdirs))
    except UnavailableInvalidChannel:
        # TODO: check condition of local directory
        local_records = set()

    source_records = query(channels, subdirs, specs)
    source_records = set(source_records)

    add_records = source_records - local_records
    removed_records = local_records - source_records
    return add_records, removed_records


def download_packages(
    records: OneOrMorePackageRecords,
    destination: Path,
    *,
    verify: bool = True,
    progress: bool = True,
) -> None:
    """Downloads packages specified from package records.

    Args:
        records: The package records of the packages to be downloaded.
        destination: The directory where the file will be downloaded.
            Additional subdirs will be created within the destination directory.
        verify: Determines if downloaded packages should be verified.
        progress: Determines if a progress bar should be shown.
    """
    records = sorted(_ensure_list(records), key=lambda rec: rec.fn)
    for record in tqdm(
        records, desc="Downloading Packages", disable=not progress, leave=False
    ):
        download_package(record, destination, verify)


def iterate(
    channels: OneOrMoreStrings, subdirs: OneOrMoreStrings
) -> Iterator[PackageRecord]:
    """Yields all the package records in a specified channels and subdirs.

    Args:
        channels: One of more upstream anaconda channels.
        subdirs: One or more anaconda subdirs (platforms).
    """
    channels = _ensure_list(channels)
    subdirs = _ensure_list(subdirs)
    channel_data = ChannelData(channels, subdirs)
    yield from channel_data.iter_records()


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

    for removed in tqdm(
        summary.removed, desc="Removing packages", disable=disable, leave=False,
    ):
        path = local / removed
        path.unlink(missing_ok=True)

    if index:
        update_index(local, progress=progress)


def query(
    channels: OneOrMoreStrings,
    subdirs: OneOrMoreStrings,
    specs: OneOrMoreStrings,
    *,
    graph_file: Optional[PathOrString] = None,
) -> Iterable[PackageRecord]:
    """Executes a query of anaconda match specifications against anaconda channels.

    Args:
        channels: One or more upstream anaconda channels.
        subdirs: One or more anaconda subdirs (platforms).
        specs: One or more anaconda match specification strings.
        graph_file: Optional save location of the qyery dependency graph.

    Returns:
        A iterable of resulting package records from the executed query.
    """
    channels = _ensure_list(channels)
    subdirs = _ensure_list(subdirs)
    specs = _ensure_list(specs)
    finder = DependencyFinder(channels, subdirs)
    records, graph = finder.search(specs)
    if graph_file is not None:
        graph_file = Path(graph_file)
    return records


def sync(
    channels: OneOrMoreStrings,
    local: PathOrString,
    subdirs: OneOrMoreStrings,
    specs: OneOrMoreStrings,
    *,
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
    local = Path(local)

    with Spinner("Reading upstream channel", enabled=progress):
        added_records, removed_records = diff(channels, local, subdirs, specs)

    destination = local if not patch else Path(patch)
    destination.mkdir(parents=True, exist_ok=True)

    if patch:
        patch_summary = destination / "patch_summary.json"
        write_patch_summary(patch_summary, added_records, removed_records)

    download_packages(added_records, destination, verify=verify, progress=progress)

    for removed_record in removed_records:
        (local / removed_record.local_path).unlink(missing_ok=True)

    if index and not patch:
        update_index(local, progress=progress)


def _ensure_list(items: Union[T, Iterable[T]]) -> List[T]:
    """Ensures that a specified variable is list of elements."""
    if not isinstance(items, Iterable):
        return cast(List[T], [items])
    if isinstance(items, str):
        return cast(List[T], [items])
    return cast(List[T], list(items))
