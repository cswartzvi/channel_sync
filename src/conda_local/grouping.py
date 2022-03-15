"""Functions and types for the generic grouping of objects."""

from collections import defaultdict
from typing import Callable, Iterable, Mapping, TypeVar

_TKey = TypeVar("_TKey")
_TValue = TypeVar("_TValue")

Grouping = Mapping[_TKey, Iterable[_TValue]]


def groupby(
    items: Iterable[_TValue], func: Callable[[_TValue], _TKey]
) -> Grouping[_TKey, _TValue]:
    """Groups items by the results of the specified function.

    Args:
        items: An iterable of items to be group.
        func: Key-producing function.

    Returns:
        Items grouped by the results of the specified function.
    """
    grouping = defaultdict(set)
    for item in items:
        key = func(item)
        grouping[key].add(item)
    return grouping
