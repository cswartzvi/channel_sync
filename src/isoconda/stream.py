from typing import Iterable, Iterator, TypeVar

T = TypeVar("T")


class UniqueStream(Iterator[T]):
    """A real-time, mutable, stream of items.

    Args:
        items: Initial items in the stream.
    """

    def __init__(self, items: Iterable[T]):
        self._data = list(items)

    def add(self, item: T):
        """Adds an item to the item stream.

        Args:
            item: Item to be added to the stream.
        """
        if item in self._data:
            return
        self._data.append(item)

    def __iter__(self) -> Iterator[T]:
        self._index = 0
        return self

    def __next__(self) -> T:
        try:
            item = self._data[self._index]
            self._index += 1
        except IndexError:
            raise StopIteration
        return item
