"""Output formatting for Slice of Pi CLI.

Table (human-readable) by default. Use --format json for piping/scripting.
"""

from __future__ import annotations

import json
import sys
from typing import Any


def format_output(data: Any, fmt: str = "table") -> None:
    """Format and print data according to the chosen format."""
    if fmt == "json":
        print(json.dumps(data, indent=2, default=str))
    elif fmt == "table":
        if isinstance(data, list):
            _print_table(data)
        elif isinstance(data, dict):
            _print_dict(data)
        else:
            print(str(data))


def _print_table(rows: list[dict]) -> None:
    """Print a list of dicts as a table using rich."""
    if not rows:
        print("(no results)")
        return

    from rich.console import Console
    from rich.table import Table

    console = Console()
    table = Table(show_header=True, header_style="bold")

    keys = list(rows[0].keys())
    for key in keys:
        table.add_column(key)

    for row in rows:
        table.add_row(*[str(row.get(k, "")) for k in keys])

    console.print(table)


def _print_dict(data: dict) -> None:
    """Print a single dict as key-value pairs using rich."""
    if not data:
        print("(no data)")
        return

    from rich.console import Console
    from rich.table import Table

    console = Console()
    table = Table(show_header=True, header_style="bold")
    table.add_column("Field")
    table.add_column("Value")

    for key, value in data.items():
        table.add_row(str(key), str(value))

    console.print(table)
