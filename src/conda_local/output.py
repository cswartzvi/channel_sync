import json
from typing import Iterable

from rich import box
from rich.console import Console
from rich.table import Table

from conda_local.group import groupby
from conda_local.adapt.package import CondaPackage
from conda_local.resolve import ResolvedPackages


def print_output(output: str, packages: ResolvedPackages) -> None:

    if output == "summary":
        _print_output_summary(packages.to_add, "Packages to Add   ")
        _print_output_summary(packages.to_remove, "Packages to Remove")
    elif output == "list":
        _print_output_list(packages.to_add, "Packages to Add")
        _print_output_list(packages.to_remove, "Packages to Remove")
    elif output == "json":
        _print_output_json(packages.to_add, packages.to_remove)


def _print_output_summary(records: Iterable[CondaPackage], label: str) -> None:
    console = Console(quiet=False)

    # Packages with similar names should be grouped into the same row
    rows = []
    groups = groupby(records, lambda record: record.name)
    for group in groups:
        number = len(list(groups[group]))
        size = sum(record.size for record in groups[group]) / 10**6
        row = (size, number, group)
        rows.append(row)

    table = Table(show_header=True, box=box.SIMPLE)
    table.add_column(f"{label} ({len(rows)})")
    table.add_column("Number")
    table.add_column("Size [MB]", justify="right")

    total_number, total_size = 0, 0.0
    for size, number, group in sorted(rows, reverse=True):
        total_number += number
        total_size += size
        table.add_row(group, f"{number}", f"{size:.2f}")
    table.add_row("Total", f"{total_number}", f"{total_size:.2f}", style="bold")
    console.print(table)


def _print_output_list(records: Iterable[CondaPackage], label: str) -> None:
    console = Console(quiet=False)
    console.print("\n" + label + ":")
    for record in sorted(records, key=lambda record: record.fn):
        print(record.fn)


def _print_output_json(
    to_add: Iterable[CondaPackage], to_remove: Iterable[CondaPackage]
) -> None:
    console = Console(quiet=False)
    data = {
        "add": [record.dump() for record in to_add],
        "remove": [record.dump() for record in to_remove],
    }
    text = json.dumps(data, indent=4)
    console.print(text)
