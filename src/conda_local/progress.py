"""Utility functions for display progress to the console."""

from contextlib import contextmanager
from typing import Iterator, Optional, Sequence, TypeVar

from tqdm import tqdm

from conda_local.external import Spinner

T = TypeVar("T", covariant=True)


def bar(
    items: Sequence[T],
    description: str = "",
    silent: Optional[bool] = None,
    leave: Optional[bool] = True,
    **kwargs,
) -> Iterator[T]:
    """Returns a type annotated iterator wrapper around ``tqdm.tqdm``.

    Args:
        items:
            An iterable of items to be decorated with a progressbar.
        description:
            The description used in the prefix of the progressbar.
        silent:
            A flag indicating that all console output should be silenced. If set to
            None, disable on non-TTY
        leave:
            If True keeps all traces of the progressbar upon termination of iteration.
            If None, will leave only if position is 0.
        kwargs:
            The remaining ``tqdm.tqdm`` parameters:

    Yields:
         An items from the original iterable decorated with a progressbar.
    """
    with tqdm(
        total=len(items), desc=description, disable=silent, leave=leave, **kwargs
    ) as pbar:
        disabled = pbar.disable
        for item in items:
            yield item
            pbar.update()
    _print_task_complete(description, silent=disabled)


@contextmanager
def spinner(description: str, silent: bool = False) -> Spinner:
    """Provides a context wrapper around a `conda.Spinner`. Similar to  ``progressbar``.

    Args:
        description:
            The description used in the prefix of the spinner.
        silent:
            A flag indicating that all console output should be silenced.
    """
    with Spinner(enabled=not silent, json=silent) as _spinner:
        yield _spinner


@contextmanager
def task(description: str, silent: bool = False):
    """Provides a context wrapper around a single task. Similar to  ``progressbar``.

    Args:
        description:
            The description used in the prefix of the task.
        silent:
            A flag indicating that all console output should be silence.
    """
    print(f"{description}:")
    yield None

    # HACK: Eww, please fix me
    CURSOR_UP_ONE = "\x1b[1A"
    ERASE_LINE = "\x1b[2K"
    print(CURSOR_UP_ONE + ERASE_LINE, end="")

    _print_task_complete(description, silent=silent)


def _print_task_complete(text: str, silent: bool = False) -> None:
    if not silent:
        print(f"{text}: done")
