# -*- coding: utf-8 -*-

from collections import defaultdict
from typing import Callable, Iterable, Mapping, TypeVar

TKey = TypeVar("TKey")
TValue = TypeVar("TValue")

Grouping = Mapping[TKey, Iterable[TValue]]


def group_by(
    items: Iterable[TValue], func: Callable[[TValue], TKey]
) -> Grouping[TKey, TValue]:
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
