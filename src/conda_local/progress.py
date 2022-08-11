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

T = TypeVar("T")


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


@contextlib.contextmanager
def monkeypatch_tqdm(console: Optional[Console] = None):
    # NOTE: Yes, I hate this as much as you do.

    old_tqdm = conda_build.index.tqdm
    with Progress(console=console) as progress:
        conda_build.index.tqdm = CondaIndexMonkeyPatch(progress)
        yield
    conda_build.index.tqdm = old_tqdm


class CondaIndexMonkeyPatch:
    def __init__(self, progress, description=""):
        self._progress = progress
        self._first = True

    def __call__(self, *args, **kwargs):
        visible = self._first
        convertor = TqdmToRichConvertor(self._progress, visible, *args, **kwargs)
        self._first = False
        return convertor


class TqdmToRichConvertor:
    def __init__(self, progress, visible, *args, **kwargs):
        self._progress = progress
        self._visible = visible

        self._kwargs = kwargs
        self._iterable = self._kwargs.get("iterable", None)
        self._description = self._kwargs.get("desc", None)
        self._total = self._kwargs.get("total", None)

        self._args = list(args)
        if self._args:
            self._iterable, *self._args = self._args
        if self._args:
            self._description, *self._args = self._args
        if self._args:
            self._total, *self._args = self._args

    def __iter__(self):
        self._task = self._progress.add_task(self._description, total=self._total)
        yield from self._progress.track(
            self._iterable,
            total=self._total,
            description=self._description,
            task_id=self._task,
        )
        self._progress.update(
            self._task, completed=True, visible=self._visible, refresh=True
        )

    def __enter__(self):
        self._task = self._progress.add_task(self._description, total=self._total)
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self._progress.update(self._task, visible=self._visible, refresh=True)

    def set_description(self, desc):
        self._progress.update(self._task, description=self._description, refresh=True)

    def update(self, n=1):
        self._progress.update(self._task, advance=n, refresh=True)
