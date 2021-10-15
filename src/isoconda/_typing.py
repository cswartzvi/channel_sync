from typing import Dict, Iterable, Mapping, Set, TypeVar

from isoconda.models import PackageRecord

T = TypeVar("T")


Grouping = Mapping[str, Iterable[T]]
PackageGrouping = Dict[str, Set[PackageRecord]]
