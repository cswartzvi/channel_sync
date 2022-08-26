import contextlib
import sys
import time
from typing import Iterable, Iterator, Optional, TypeVar

import conda_build.index
import tqdm
from rich.console import Console
from rich.control import Control

T = TypeVar("T")

STANDARD_BAR_FORMAT = (
    "{desc} {percentage:3.0f}%|"
    "{bar:40}"
    "| {n_fmt}/{total_fmt} [E: {elapsed} R: {remaining}] {postfix}"
)

MONKEYPATCH_BAR_FORMAT = (
    "   {desc:35} {percentage:3.0f}%|"
    "{bar:40}"
    "| {n_fmt}/{total_fmt} [E: {elapsed}] R: N/A] {postfix}"
)

BAR_TEXT_LENGTH = 22


class Display:
    """Standardizes display elements for the application.

    Args:
        console: Rich console where output will be presented.
    """

    def __init__(self, console: Console, disable: Optional[bool] = None) -> None:
        self.console = console

        # Flag to disable animations (not necessarily output).
        if sys.stdout.isatty():
            self.disable = self.console.quiet if disable is None else disable
        else:
            self.disable = True

    def progress(self, items: Iterable[T], message) -> Iterator[T]:
        """Iterates over items with progress bar."""
        message = self._parse_message(message)
        start = time.time()

        yield from tqdm.tqdm(
            items,
            desc=message,
            bar_format=STANDARD_BAR_FORMAT,
            # colour="cyan",
            disable=self.disable,
            # ascii=True,
            leave=False,
        )

        elapsed = time.time() - start
        self.console.print(f"{message} [bold cyan]Done ({round(elapsed)}s)[/]")

    @contextlib.contextmanager
    def status(self, message: str) -> Iterator[None]:
        """Context for displaying working status."""
        message = self._parse_message(message)

        if not self.disable:
            self.console.print(f"{message} [bold cyan]...[/]", end="")

        start = time.time()
        yield
        elapsed = time.time() - start

        if not self.disable:
            self.console.print("", end="\r")

        self.console.print(f"{message} [bold cyan]Done ({round(elapsed)}s)[/]")

    @contextlib.contextmanager
    def status_monkeypatch_conda_index(self, message: str) -> Iterator[None]:
        """Context for temporarily monkeypatch of the conda index progress."""
        # NOTE: Yes, I hate this as much as you do.

        def patched_tqdm(*args, **kwargs):
            # kwargs["ascii"] = True
            kwargs["bar_format"] = MONKEYPATCH_BAR_FORMAT
            kwargs["disable"] = self.disable
            # kwargs["colour"] = "cyan"
            return tqdm.tqdm(*args, **kwargs)

        old_tqdm = conda_build.index.tqdm
        message = self._parse_message(message)
        try:
            conda_build.index.tqdm = patched_tqdm

            if not self.disable:
                self.console.print(f"{message} [bold cyan]...[/]")  # no newline

            start = time.time()
            yield
            elapsed = time.time() - start

            if not self.disable:
                self.console.control(Control.move(y=-1))
            self.console.print(f"{message} [bold cyan]Done ({round(elapsed)}s)[/]")
        finally:
            conda_build.index.tqdm = old_tqdm

    def _parse_message(self, message: str) -> str:
        message = message.strip()
        if message:
            message += ":"
        return " " + message
