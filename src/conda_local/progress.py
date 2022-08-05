import contextlib
from typing import Iterable, Iterator, TypeVar

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


def iterate_progress(items: Iterable[T], message: str, console: Console) -> Iterator[T]:
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
def start_status(message: str, console: Console) -> Iterator[None]:
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
