import contextlib
import sys
from typing import Iterable, Iterator, Optional, TypeVar

import tqdm
import conda_build.index
from rich.console import Console
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)

T = TypeVar("T")

STANDARD_BAR_FORMAT = (
    "{desc} {percentage:3.0f}%|"
    "{bar:60}"
    "| {n_fmt}/{total_fmt} [E: {elapsed} R: {remaining}] {postfix}"
)

MONKEYPATCH_BAR_FORMAT = (
    "{desc:>35} {percentage:3.0f}%|"
    "{bar:50}"
    "| {n_fmt}/{total_fmt} [E: {elapsed} R: {remaining}] {postfix}"
)


def iterate_progress(
    items: Iterable[T], message: str, console: Optional[Console] = None
) -> Iterator[T]:
    yield from tqdm.tqdm(
        items,
        desc=message,
        ascii=True,
        bar_format=STANDARD_BAR_FORMAT,
        colour="cyan",
    )


@contextlib.contextmanager
def start_status(message: str, console: Console) -> Iterator[None]:
    console.print(message + " ... ", end="", style="default")
    yield
    console.print("[cyan]Done[/cyan]")


@contextlib.contextmanager
def start_index_monkeypatch(message: str, console: Console):
    # NOTE: Yes, I hate this as much as you do.
    old_tqdm = conda_build.index.tqdm
    try:
        console.print(message + " ... ", style="default")
        conda_build.index.tqdm = CondaIndexMonkeyPatch(console.quiet)
        yield
        sys.stdout.write("\033[K")
        console.print("[cyan]Done[/cyan]")
    finally:
        conda_build.index.tqdm = old_tqdm


class CondaIndexMonkeyPatch:
    def __init__(self, quiet=False):
        self._quiet = quiet

    def __call__(self, *args, **kwargs):
        kwargs["ascii"] = True
        kwargs["bar_format"] = MONKEYPATCH_BAR_FORMAT
        kwargs["disable"] = self._quiet
        kwargs["colour"] = "cyan"

        patched_tqdm = tqdm.tqdm(*args, **kwargs)
        self._first = False
        return patched_tqdm
