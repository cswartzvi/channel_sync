"""A general collection of utility functions."""

from contextlib import contextmanager
from typing import Iterable, Iterator, List, Optional, Sequence, TypeVar, Union, cast

from tqdm import tqdm

T = TypeVar("T", covariant=True)


def ensure_list(items: Union[T, Iterable[T]]) -> List[T]:
    """Ensures that an input parameter is list of elements."""
    results: List[T]
    if not isinstance(items, Iterable):
        results = [items]
    elif isinstance(items, str):
        results = cast(List[T], [items])
    else:
        results = list(items)
    return results


def _print_task_complete(text: str, silent: bool = False) -> None:
    if not silent:
        print(f"{text}: done")


def progressbar(
    items: Sequence[T],
    desc: str = "",
    disable: Optional[bool] = None,
    leave: Optional[bool] = True,
    **kwargs,
) -> Iterator[T]:
    """Returns a type annotated iterator wrapper around ``tqdm.tqdm``.

    Args:
        items:
            An iterable of items to be decorated with a progressbar.
        desc:
            The description used in the prefix of the progressbar.
        disable:
            A flag indicating whether to disable the entire progressbar wrapper
            If set to None, disable on non-TTY
        leave:
            If True keeps all traces of the progressbar upon termination of iteration.
            If None, will leave only if position is 0.
        kwargs:
            The remaining ``tqdm.tqdm`` parameters:

    Yields:
         An items from the original iterable decorated with a progressbar.
    """
    with tqdm(
        total=len(items), desc=desc, disable=disable, leave=leave, **kwargs
    ) as bar:
        disabled = bar.disable
        for item in items:
            yield item
            bar.update()
    _print_task_complete(desc, silent=disabled)


@contextmanager
def task(desc: str, disable: bool = False):
    """Provides a context wrapper around a single task. Similar to  ``progressbar``.

    Args:
        desc:
            The description used in the prefix of the progressbar.
        disable:
            A flag indicating whether to disable the entire task wrapper.
    """
    print(f"{desc}:")
    yield None

    # HACK: Eww, please fix me
    CURSOR_UP_ONE = "\x1b[1A"
    ERASE_LINE = "\x1b[2K"
    print(CURSOR_UP_ONE + ERASE_LINE, end="")

    _print_task_complete(desc, silent=disable)
