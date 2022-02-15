"""Utilities for iteration and grouping."""

from collections import defaultdict
from typing import Callable, Iterable, Iterator, Mapping, TypeVar

_T = TypeVar("_T")
_TKey = TypeVar("_TKey")
_TValue = TypeVar("_TValue")

Grouping = Mapping[_TKey, Iterable[_TValue]]


class UniqueStream(Iterator[_T]):
    """A stream of items that is mutable during iteration.

    Args:
        items: Initial items in the stream.
    """

    def __init__(self, items: Iterable[_T]):
        self._data = list(items)

    def add(self, item: _T):
        """Adds an item to the item stream.

        Args:
            item: Item to be added to the stream.
        """
        if item in self._data:
            return
        self._data.append(item)

    def __iter__(self) -> Iterator[_T]:
        self._index = 0
        return self

    def __next__(self) -> _T:
        try:
            item = self._data[self._index]
            self._index += 1
        except IndexError:
            raise StopIteration
        return item


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
