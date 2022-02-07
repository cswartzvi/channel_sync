"""High-level api functions for conda-local."""

import datetime
from pathlib import Path
from typing import Iterable, Iterator, List, Optional, Set, Tuple, TypeVar, Union, cast

from tqdm import tqdm

from conda_local.adapters import (
    ChannelData,
    PackageRecord,
    UnavailableInvalidChannel,
    download_package,
    update_index,
)
from conda_local.deps import DependencyFinder

T = TypeVar("T", covariant=True)
OneOrMoreStrings = Union[str, Iterable[str]]
OneOrMorePackageRecords = Union[PackageRecord, Iterable[PackageRecord]]
PathOrString = Union[str, Path]


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


def merge():
    pass


def query(
    channels: OneOrMoreStrings,
    subdirs: OneOrMoreStrings,
    specs: OneOrMoreStrings,
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
    index: bool = True,
    verify: bool = True,
    patch: bool = False,
    patch_folder: PathOrString = "",
    progress: bool = True,
) -> None:
    """Syncs a local anaconda channel with upstream anaconda channels.

    Args:
        channels: One or more upstream anaconda channels.
        local: The location of the local anaconda channel.
        subdirs: One or more anaconda subdirs (platforms).
        specs: One or more anaconda match specification strings
        index: Determines if the local channel index should be updated.
        verify: Determines if downloaded packages should be verified.
        patch: Determines if packages should be downloaded to a separate patch
            directory (see also conda_local.api.merge).
        patch_folder: The override path of the patch directory.
        progress: Determines if a progress bar should be shown.
    """
    local = Path(local)
    if progress:
        print("Reading channels...")
    added_records, removed_records = diff(channels, local, subdirs, specs)

    if patch:
        if patch_folder:
            local = Path(patch_folder)
        else:
            now = datetime.datetime.now()
            local = Path(f"patch_{now.strftime('%Y%m%d_%H%M%S')}")

    local.mkdir(parents=True, exist_ok=True)
    download_packages(added_records, local, verify=verify, progress=progress)
    for removed_record in removed_records:
        (local / removed_record.local_path).unlink(missing_ok=True)
    if index:
        update_index(local, progress=progress)


def verify():
    pass


def _ensure_list(items: Union[T, Iterable[T]]) -> List[T]:
    """Ensures that a specified variable is list of elements."""
    if not isinstance(items, Iterable):
        return cast(List[T], [items])
    if isinstance(items, str):
        return cast(List[T], [items])
    return cast(List[T], list(items))
