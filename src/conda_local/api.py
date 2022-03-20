"""High-level api functions for conda-local."""

import shutil
from pathlib import Path
from typing import Dict, Iterable, Iterator, Optional, Union

from conda_local.deps import DependencyFinder
from conda_local.external import (
    PackageRecord,
    Spinner,
    compare_records,
    download_package,
    fetch_patch_instructions,
    get_default_subdirs,
    iter_channel,
    setup_channel,
    update_index,
)
from conda_local.grouping import groupby
from conda_local.utils import ensure_list, progressbar, task

OneOrMoreStrings = Union[str, Iterable[str]]
PathOrString = Union[str, Path]


def iterate(
    channel: str, subdirs: Optional[OneOrMoreStrings] = None,
) -> Iterator[PackageRecord]:
    """Yields all the package records in a specified channels and subdirs.

    Args:
        channels: One of more upstream anaconda channels.
        subdirs: One or more anaconda subdirs (platforms).
    """
    if subdirs is None:
        subdirs = get_default_subdirs()
    subdirs = ensure_list(subdirs)

    records = iter_channel(channel, subdirs)
    yield from records


def merge(
    local: PathOrString, patch: PathOrString, silent: bool = True,
):
    """Merges a patch produced by conda_local with a local anaconda channel.

    Args:
        local: The location of the local anaconda channel.
        patch: The location of the conda_local patch directory.
        index: Determines if the local channel index should be updated.

    """
    patch = Path(patch)
    local = Path(local)

    with Spinner("Copying patch", enabled=not silent):
        for file in patch.glob("**/*"):
            if file.is_file():
                shutil.copy(file, local / file.relative_to(patch))

    with task("Updating index"):
        update_index(local, silent=silent, subdirs=[])


def query(
    channel: str,
    specs: OneOrMoreStrings,
    subdirs: Optional[OneOrMoreStrings] = None,
    graph_file: Optional[PathOrString] = None,
) -> Iterable[PackageRecord]:
    """Executes a query of anaconda match specifications against anaconda channels.

    Args:
        channels: One or more upstream anaconda channels.
        specs: One or more anaconda match specification strings.
        subdirs: One or more anaconda subdirs (platforms).
        graph_file: Optional save location of the query dependency graph.

    Returns:
        A iterable of resulting package records from the executed query.
    """
    specs = ensure_list(specs)
    if not subdirs:
        subdirs = get_default_subdirs()
    subdirs = ensure_list(subdirs)

    finder = DependencyFinder(channel, subdirs)
    records, graph = finder.search(specs)

    if graph_file is not None:
        graph_file = Path(graph_file)

    return records


def sync(
    local: PathOrString,
    upstream: str,
    specs: OneOrMoreStrings,
    subdirs: Optional[OneOrMoreStrings] = None,
    patch: Optional[PathOrString] = None,
    silent: bool = True,
    keep: bool = False,
    dry_run: bool = False,
) -> Dict:
    """Syncs a local anaconda channel with upstream anaconda channels.

    Args:
        channels: One or more upstream anaconda channels.
        local: The location of the local anaconda channel.
        subdirs: One or more anaconda subdirs (platforms).
        specs: One or more anaconda match specification strings
        patch: The location of the patch folder.
        progress: Determines if a progress bar should be shown.
    """
    local = setup_channel(local)
    specs = ensure_list(specs)

    if not subdirs:
        subdirs = get_default_subdirs()
    subdirs = ensure_list(subdirs)

    destination = local if not patch else Path(patch)
    destination.mkdir(parents=True, exist_ok=True)

    with Spinner("Reading local channel", enabled=not silent, json=silent):
        local_records = iterate(local.resolve().as_uri(), subdirs=subdirs)

    with Spinner("Querying upstream channel", enabled=not silent, json=silent):
        upstream_records = query(upstream, specs, subdirs=subdirs)

    added, removed = compare_records(upstream_records, local_records)

    if keep:
        removed.clear()

    if not dry_run:
        removed_by_subdir = groupby(removed, lambda rec: rec.subdir)

        for subdir in progressbar(
            subdirs, desc="Downloading patch instructions", disable=silent, leave=False,
        ):
            fetch_patch_instructions(
                upstream, destination, subdir, removed_by_subdir.get(subdir)
            )

        for record in progressbar(
            sorted(added, key=lambda rec: rec.fn),
            desc="Downloading packages",
            disable=silent,
            leave=False,
        ):
            download_package(record, destination)

        if not patch:
            with task("Updating index"):
                update_index(local, silent=silent, subdirs=subdirs)

    summary = {
        "added": sorted(rec.fn for rec in added),
        "removed": sorted(rec.fn for rec in removed),
    }

    return summary
