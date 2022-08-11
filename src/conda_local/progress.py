import contextlib
from typing import Iterable, Iterator, Optional, TypeVar

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
from rich.progress import track
from tqdm import tqdm

T = TypeVar("T")


class TqdmMonkeyPatch:

    def __init__(self, *args, **kwargs) -> None:
        self._args = args
        self._kwargs = kwargs

        self._kwargs.pop("disable", None)
        self._kwargs["disable"] = True
        print("New tqdm monkeypatch")

    def __iter__(self):
        iterable, *args = self._args
        desc = self._kwargs.pop("desc", "")
        for item in track(iterable, description=desc, ):
            yield item

    def __enter__(self):
        print("Start context")
        return tqdm(*self._args, **self._kwargs)

    def __exit__(self, exc_type, exc_value, exc_traceback):
        print("Ending context")


def monkeypatch_tqdmm():
    conda_build.index.tqdm = TqdmMonkeyPatch


def iterate_progress(
    items: Iterable[T], message: str, console: Optional[Console] = None
) -> Iterator[T]:
    progress = Progress(
        SpinnerColumn(spinner_name="line", finished_text="[bold green]✓[/bold green]"),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        MofNCompleteColumn(),
        TimeRemainingColumn(),
        TimeElapsedColumn(),
        console=console,
    )
    with progress:
        yield from progress.track(items, description=message)


@contextlib.contextmanager
def start_status(message: str, console: Optional[Console]) -> Iterator[None]:
    with Progress(
        SpinnerColumn(spinner_name="line", finished_text="[bold green]✓[/bold green]"),
        TextColumn("[progress.description]{task.description}"),
        # SpinnerColumn(spinner_name="point", finished_text="[green]✓[/green]"),
        console=console,
    ) as progress:
        task = progress.add_task(message, total=1)
        yield
        progress.update(task, advance=1)
        progress.update(task)
