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
        items: An iterable of items to be grouped.
        func: A function that generates the key used to group items.

    Returns:
        The original items grouped by the results of the specified function.
    """
    grouping = defaultdict(set)
    for item in items:
        key = func(item)
        grouping[key].add(item)
    return grouping
