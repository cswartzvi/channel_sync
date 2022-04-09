"""High-level api functions for conda-local."""

import shutil
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, Optional, TypeVar, Union, cast

from conda_local import progress
from conda_local.external import (
    PackageRecord,
    compute_relative_complements,
    download_package,
    fetch_patch_instructions,
    get_default_subdirs,
    get_local_channel_subdirs,
    iter_channel,
    setup_channel,
    update_index,
)
from conda_local.graph import construct_dependency_graph
from conda_local.grouping import groupby

OneOrMoreStrings = Union[str, Iterable[str]]
PathOrString = Union[str, Path]
_T = TypeVar("_T", covariant=True)


def iterate(
    channel: PathOrString, subdirs: Optional[OneOrMoreStrings] = None,
) -> Iterator[PackageRecord]:
    """Yields all the package records in a specified anaconda channel.

    Args:
        channel: An anaconda channel url, identifier, or local path.
        subdirs: One or more anaconda subdirs (platforms).
    """
    channel = _process_channel_arg(channel)
    subdirs = _process_subdirs_arg(subdirs)

    records = iter_channel(channel, subdirs)
    yield from records


def merge(
    target: PathOrString, patch: PathOrString, silent: bool = True,
):
    """Merges a patch produced by conda_local with a local anaconda channel.

    Args:
        local: The location of the local anaconda channel.
        patch: The location of the conda_local patch directory.
        index: Determines if the local channel index should be updated.

    """
    patch = Path(patch)
    target = Path(target)

    subdirs = get_local_channel_subdirs(target)

    with progress.spinner("Copying patch", silent=silent):
        for file in patch.glob("**/*"):
            if file.is_file():
                shutil.copy(file, target / file.relative_to(patch))

    with progress.task("Updating index", silent=silent):
        update_index(target, silent=silent, subdirs=subdirs)


def query(
    channel: PathOrString,
    specs: OneOrMoreStrings,
    subdirs: Optional[OneOrMoreStrings] = None,
    latest: bool = False,
    graph_file: Optional[PathOrString] = None,
) -> Iterable[PackageRecord]:
    """Query an anaconda channel using the match specification query language.

    For more information on the match specification query language see:
    https://docs.conda.io/projects/conda/en/latest/user-guide/concepts/pkg-specs.html#package-match-specifications  # noqa

    Args:
        channels: One or more upstream anaconda channels.
        specs: One or more anaconda match specification strings.
        subdirs: One or more anaconda subdirs (platforms).
        graph_file: Optional save location of the query dependency graph.

    Returns:
        A iterable of resulting package records from the executed query.
    """
    channel = _process_channel_arg(channel)
    specs = _ensure_list(specs)
    subdirs = _process_subdirs_arg(subdirs)

    graph = construct_dependency_graph(channel, subdirs, specs)
    records = graph.records

    return records


def synchronize(
    target: PathOrString,
    upstream: PathOrString,
    specs: OneOrMoreStrings,
    subdirs: Optional[OneOrMoreStrings] = None,
    patch: Optional[PathOrString] = None,
    silent: bool = True,
    keep: bool = False,
    latest: bool = False,
    dry_run: bool = False,
) -> Dict:
    """Synchronizes a target anaconda channel to an upstream anaconda channel.

    Args:
        target:

    """
    target = Path(target)
    setup_channel(target)
    upstream = _process_channel_arg(upstream)
    specs = _ensure_list(specs)
    subdirs = _process_subdirs_arg(subdirs)

    destination = target if not patch else Path(patch)
    destination.mkdir(parents=True, exist_ok=True)

    with progress.spinner("Reading local channel", silent=silent):
        local_records = iterate(target.resolve().as_uri(), subdirs=subdirs)

    with progress.spinner("Querying upstream channel", silent=silent):
        upstream_records = query(upstream, specs, subdirs=subdirs, latest=latest)

    added, removed = compute_relative_complements(upstream_records, local_records)

    if keep:
        removed.clear()

    if not dry_run:
        removed_by_subdir = groupby(removed, lambda rec: rec.subdir)

        for subdir in progress.bar(
            subdirs,
            description="Downloading patch instructions",
            silent=silent,
            leave=False,
        ):
            fetch_patch_instructions(
                upstream, destination, subdir, removed_by_subdir.get(subdir)
            )

        for record in progress.bar(
            sorted(added, key=lambda rec: rec.fn),
            description="Downloading packages",
            silent=silent,
            leave=False,
        ):
            download_package(record, destination)

        if not patch:
            with progress.task("Updating index", silent=silent):
                update_index(target, silent=silent, subdirs=subdirs)

    summary = {
        "added": sorted(rec.fn for rec in added),
        "removed": sorted(rec.fn for rec in removed),
    }

    return summary


def _ensure_list(items: Union[_T, Iterable[_T]]) -> List[_T]:
    """Ensures that an argument is a list of elements."""
    results: List[_T]
    if not isinstance(items, Iterable):
        results = [items]
    elif isinstance(items, str):
        results = cast(List[_T], [items])
    else:
        results = list(items)
    return results


def _process_channel_arg(channel: PathOrString) -> str:
    """Processes a channel argument, returning a string."""
    if isinstance(channel, Path):
        return channel.resolve().as_uri()
    return str(channel)


def _process_subdirs_arg(subdirs: Optional[OneOrMoreStrings] = None) -> List[str]:
    """Processes a subdir argument, returning a list of strings."""
    if not subdirs:
        return list(get_default_subdirs())
    return _ensure_list(subdirs)
