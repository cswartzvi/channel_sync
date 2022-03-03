"""Functionality for reading and writing patch summary files."""

import json
import os.path
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, List

from conda_local import CondaLocalException
from conda_local._typing import PathOrString
from conda_local.external import PackageRecord


class InvalidPatchSummary(CondaLocalException):
    pass


@dataclass
class PatchSummary:
    added: List[str]
    removed: List[str]


def read_patch_summary(path: PathOrString) -> PatchSummary:
    """Reads a patch summary file

    Args:
        path: The location of the patch summary file.

    Returns:
        A patch summary object.
    """
    path = Path(path)
    with path.open("rt") as file:
        data = json.load(file)

        added = data.get("added", None)
        if not isinstance(added, list):
            raise InvalidPatchSummary("'added' has missing or incorrect format")

        removed = data.get("removed", None)
        if not isinstance(removed, list):
            raise InvalidPatchSummary("'removed' has missing or incorrect format")

        summary = PatchSummary(added=added, removed=removed)
        return summary


def write_patch_summary(
    path: PathOrString, added: Iterable[PackageRecord], removed: Iterable[PackageRecord]
) -> None:
    """Writes a patch summary to a file.

    Args:
        path: Location of the patch summary file.
        added: An iterable of added package records.
        removed: An iterable of removed package records.
    """
    path = Path(path)
    summary = PatchSummary(
        added=[os.path.join(rec.subdir, rec.fn) for rec in added],
        removed=[os.path.join(rec.subdir, rec.fn) for rec in removed],
    )

    with path.open("wt") as file:
        json.dump(asdict(summary), file)
