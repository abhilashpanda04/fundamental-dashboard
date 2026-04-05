"""Unit tests for the ``TableBuilder`` (Builder Pattern)."""

from __future__ import annotations

import pytest
from rich import box
from rich.table import Table

from finscope.ui.builders import (
    TableBuilder,
    comparison_table,
    financial_table,
    simple_table,
)


class TestTableBuilder:
    def test_build_returns_table_instance(self):
        table = TableBuilder("Test").build()
        assert isinstance(table, Table)

    def test_title_set_correctly(self):
        table = TableBuilder("My Title").build()
        assert table.title == "My Title"

    def test_columns_added(self):
        table = (
            TableBuilder("T")
            .column("Col A")
            .column("Col B")
            .build()
        )
        assert len(table.columns) == 2

    def test_column_kwargs_forwarded(self):
        table = (
            TableBuilder("T")
            .column("Metric", style="bold", min_width=20)
            .build()
        )
        col = table.columns[0]
        assert col.style == "bold"
        assert col.min_width == 20

    def test_rows_added(self):
        table = (
            TableBuilder("T")
            .column("A")
            .column("B")
            .row("x", "y")
            .row("p", "q")
            .build()
        )
        assert table.row_count == 2

    def test_rows_bulk_added(self):
        table = (
            TableBuilder("T")
            .column("A")
            .rows([("r1",), ("r2",), ("r3",)])
            .build()
        )
        assert table.row_count == 3

    def test_border_style_applied(self):
        table = TableBuilder("T").border("magenta").build()
        assert table.border_style == "magenta"

    def test_box_style_applied(self):
        table = TableBuilder("T").box_style(box.SIMPLE_HEAVY).build()
        assert table.box is box.SIMPLE_HEAVY

    def test_method_chaining_returns_self(self):
        builder = TableBuilder("T")
        result = builder.title("New").border("blue").column("X").row("v")
        assert result is builder

    def test_no_header(self):
        table = TableBuilder("T").no_header().build()
        assert table.show_header is False

    def test_empty_title_yields_no_title(self):
        table = TableBuilder("").build()
        assert table.title is None

    def test_multiple_rows_different_widths(self):
        """Rows with different widths should not crash."""
        table = (
            TableBuilder("T")
            .column("A")
            .column("B")
            .row("a", "b")
            .build()
        )
        assert table.row_count == 1


class TestPreConfiguredFactories:
    def test_financial_table_border_is_magenta(self):
        t = financial_table("Income Statement").build()
        assert t.border_style == "magenta"

    def test_comparison_table_border_is_blue(self):
        t = comparison_table("Compare").build()
        assert t.border_style == "blue"

    def test_simple_table_custom_border(self):
        t = simple_table("Table", border="green").build()
        assert t.border_style == "green"

    def test_simple_table_default_border(self):
        t = simple_table("Table").build()
        assert t.border_style == "cyan"

    def test_factories_return_builder_not_table(self):
        assert isinstance(financial_table("T"), TableBuilder)
        assert isinstance(comparison_table("T"), TableBuilder)
        assert isinstance(simple_table("T"), TableBuilder)
