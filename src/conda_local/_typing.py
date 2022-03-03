"""Contains common type hints for conda-local."""

from pathlib import Path
from typing import Iterable, Union

from conda_local.external import PackageRecord

OneOrMoreStrings = Union[str, Iterable[str]]
OneOrMorePackageRecords = Union[PackageRecord, Iterable[PackageRecord]]
PathOrString = Union[str, Path]
