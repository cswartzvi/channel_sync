import contextlib
from typing import Iterable, Iterator, TypeVar

import conda_build.index
import tqdm
from rich.console import Console
from rich.control import Control

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
    items: Iterable[T], console: Console, message: str, length: int = 0
) -> Iterator[T]:
    message = message.strip() + ":"
    if length:
        message = f"{message:{length}}"
    yield from tqdm.tqdm(
        items,
        desc=message,
        ascii=True,
        bar_format=STANDARD_BAR_FORMAT,
        colour="cyan",
        disable=console.quiet,
    )


@contextlib.contextmanager
def start_status(
    console: Console,
    message: str,
) -> Iterator[None]:
    console.print(message.strip() + ": [cyan]...[/cyan]", end="")
    yield
    console.control(Control.move(x=-3))
    console.print("[cyan]Done[/cyan]")


@contextlib.contextmanager
def start_index_monkeypatch(console: Console, message: str):
    # NOTE: Yes, I hate this as much as you do.

    def patched_tqdm(*args, **kwargs):
        kwargs["ascii"] = True
        kwargs["bar_format"] = MONKEYPATCH_BAR_FORMAT
        kwargs["disable"] = console.quiet
        kwargs["colour"] = "cyan"
        return tqdm.tqdm(*args, **kwargs)

    message = message.strip()
    old_tqdm = conda_build.index.tqdm
    try:
        conda_build.index.tqdm = patched_tqdm
        console.print(message + ": [cyan]...[/cyan]")
        yield
        console.control(Control.move(y=-1))
        console.print(message + ": [cyan]Done[/cyan]")
    finally:
        conda_build.index.tqdm = old_tqdm
