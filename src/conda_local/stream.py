import logging
from collections.abc import Hashable
from typing import Dict, Iterable, Iterator, Set, TypeVar

_LOGGER = logging.getLogger(__name__)

_T = TypeVar("_T", bound=Hashable)


class UniqueAppendableStream(Iterator[_T]):
    """A stream of unique items that is appendable during iteration.

    Args:
        items: Initial items in the stream.
    """

    def __init__(self, items: Iterable[_T]):
        self._to_process: Dict[_T, None] = dict.fromkeys(items)
        self._processed: Set[_T] = set()

    def append(self, item: _T) -> None:
        """Appends a new unique item to the end of a the stream.

        Args:
            item: Generic item to append to the stream. If this item already exists in
                the stream (even if it has already been processed) it is ignored.
        """
        if item in self._processed:
            return  # already processed
        self._to_process.update({item: None})  # ignored if already processed

    def __iter__(self) -> Iterator[_T]:
        return self

    def __next__(self) -> _T:
        try:
            item = self._to_process.popitem()[0]
        except KeyError:
            raise StopIteration
        self._processed.add(item)
        return item
