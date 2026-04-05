"""Rich table builder — Builder Pattern.

``TableBuilder`` provides a fluent, chainable API for constructing Rich
``Table`` objects.  Instead of repeating the same ``Table(...)`` / ``add_column``
/ ``add_row`` boilerplate across every renderer, callers describe what they
want and call ``.build()`` to obtain the finished table.

Example::

    table = (
        TableBuilder("Key Ratios")
        .border("cyan")
        .column("Metric", style="bold", min_width=20)
        .column("Value", justify="right", min_width=15)
        .row("P/E Ratio", "25.4")
        .row("Beta", "1.12")
        .build()
    )
    console.print(table)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from rich import box as rich_box
from rich.table import Table

__all__ = ["TableBuilder", "financial_table", "comparison_table", "simple_table"]


@dataclass
class _ColumnSpec:
    name: str
    kwargs: dict[str, Any] = field(default_factory=dict)


class TableBuilder:
    """Fluent builder for Rich ``Table`` objects (Builder Pattern).

    All setter methods return ``self`` for method chaining.
    """

    def __init__(self, title: str = "") -> None:
        self._title = title
        self._border_style = "cyan"
        self._box = rich_box.ROUNDED
        self._columns: list[_ColumnSpec] = []
        self._rows: list[tuple[str, ...]] = []
        self._show_header = True
        self._padding = (0, 1)

    # ── Builder setters ───────────────────────────────────────────────────────

    def title(self, title: str) -> "TableBuilder":
        """Set the table title."""
        self._title = title
        return self

    def border(self, style: str) -> "TableBuilder":
        """Set the border colour / style."""
        self._border_style = style
        return self

    def box_style(self, box_style) -> "TableBuilder":
        """Set the Rich box style (e.g. ``rich.box.SIMPLE_HEAVY``)."""
        self._box = box_style
        return self

    def no_header(self) -> "TableBuilder":
        """Hide the column header row."""
        self._show_header = False
        return self

    def column(self, name: str, **kwargs: Any) -> "TableBuilder":
        """Append a column definition.

        All keyword arguments are forwarded to ``Table.add_column``.
        """
        self._columns.append(_ColumnSpec(name=name, kwargs=kwargs))
        return self

    def row(self, *values: str) -> "TableBuilder":
        """Append a data row.

        Values are passed as positional strings to ``Table.add_row``.
        """
        self._rows.append(values)
        return self

    def rows(self, rows: list[tuple[str, ...]]) -> "TableBuilder":
        """Append multiple rows at once."""
        self._rows.extend(rows)
        return self

    # ── Terminal step ────────────────────────────────────────────────────────

    def build(self) -> Table:
        """Construct and return the configured ``Table`` object."""
        table = Table(
            title=self._title or None,
            box=self._box,
            border_style=self._border_style,
            show_header=self._show_header,
            padding=self._padding,
        )

        for col in self._columns:
            table.add_column(col.name, **col.kwargs)

        for row in self._rows:
            table.add_row(*row)

        return table


# ── Pre-configured table factories ────────────────────────────────────────────


def financial_table(title: str) -> TableBuilder:
    """Return a pre-styled builder for financial statement tables."""
    return TableBuilder(title).border("magenta").box_style(rich_box.ROUNDED)


def comparison_table(title: str) -> TableBuilder:
    """Return a pre-styled builder for comparison / watchlist tables."""
    return TableBuilder(title).border("blue").box_style(rich_box.ROUNDED)


def simple_table(title: str, border: str = "cyan") -> TableBuilder:
    """Return a minimal builder for general-purpose tables."""
    return TableBuilder(title).border(border).box_style(rich_box.SIMPLE_HEAVY)
