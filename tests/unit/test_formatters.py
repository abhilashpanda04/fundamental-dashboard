"""Unit tests for ``dashboard.ui.formatters``.

All formatter functions are pure, so no mocking is needed.
"""

from __future__ import annotations

import pytest

from dashboard.ui.formatters import (
    format_currency,
    format_number,
    format_pct,
    format_return,
    make_sparkline,
    safe_float,
)


class TestFormatNumber:
    def test_none_returns_na(self):
        assert format_number(None) == "[dim]N/A[/dim]"

    def test_billions(self):
        result = format_number(2_700_000_000_000)
        assert "2700.00B" in result or "2.70" in result  # flexible for different scales
        assert "B" in result

    def test_millions(self):
        result = format_number(394_328_000_000)
        assert "M" in result or "B" in result

    def test_small_float_four_decimals(self):
        result = format_number(0.0056)
        assert result == "0.0056"

    def test_regular_float_two_decimals(self):
        result = format_number(28.5)
        assert result == "28.50"

    def test_non_numeric_str(self):
        result = format_number("hello")  # type: ignore[arg-type]
        assert result == "hello"

    def test_negative_billion(self):
        result = format_number(-1_500_000_000)
        assert "B" in result
        assert "-" in result


class TestFormatPct:
    def test_none_returns_na(self):
        assert format_pct(None) == "[dim]N/A[/dim]"

    def test_positive_is_green(self):
        result = format_pct(1.25)
        assert "green" in result
        assert "+1.25%" in result

    def test_negative_is_red(self):
        result = format_pct(-2.5)
        assert "red" in result
        assert "-2.50%" in result

    def test_zero_is_green(self):
        result = format_pct(0.0)
        assert "green" in result

    def test_format_includes_sign(self):
        assert "+" in format_pct(5.0)
        assert "-" in format_pct(-5.0)


class TestFormatCurrency:
    def test_none_returns_na(self):
        assert format_currency(None) == "[dim]N/A[/dim]"

    def test_billion_suffix(self):
        result = format_currency(2_500_000_000)
        assert "2.50B" in result

    def test_million_suffix(self):
        result = format_currency(125_000_000)
        assert "125.00M" in result

    def test_thousand_suffix(self):
        result = format_currency(55_000)
        assert "55.00K" in result

    def test_small_value_four_decimals(self):
        result = format_currency(10.5)
        assert "10.5000" in result

    def test_with_currency_prefix(self):
        result = format_currency(1_000_000_000, currency="USD")
        assert "USD" in result
        assert "B" in result

    def test_non_numeric_fallback(self):
        result = format_currency("N/A")
        assert result == "N/A"


class TestFormatReturn:
    def test_none_returns_na(self):
        assert format_return(None) == "[dim]N/A[/dim]"

    def test_fraction_converted_to_percent(self):
        # 0.15 → 15%
        result = format_return(0.15)
        assert "15.00%" in result
        assert "green" in result

    def test_percentage_value_kept(self):
        result = format_return(15.0)
        assert "15.00%" in result
        assert "green" in result

    def test_negative_fraction(self):
        result = format_return(-0.05)
        assert "red" in result
        assert "5.00%" in result

    def test_negative_percent(self):
        result = format_return(-12.5)
        assert "red" in result

    def test_zero_is_green(self):
        result = format_return(0.0)
        assert "green" in result


class TestMakeSparkline:
    def test_empty_returns_no_data(self):
        assert make_sparkline([]) == "[dim]No data[/dim]"

    def test_single_value_returns_no_data(self):
        assert make_sparkline([100.0]) == "[dim]No data[/dim]"

    def test_uptrend_is_green(self):
        result = make_sparkline([100.0, 110.0, 120.0])
        assert "green" in result

    def test_downtrend_is_red(self):
        result = make_sparkline([120.0, 110.0, 100.0])
        assert "red" in result

    def test_contains_sparkline_chars(self):
        result = make_sparkline([100.0, 102.0, 104.0, 106.0])
        spark_chars = "▁▂▃▄▅▆▇█"
        assert any(c in result for c in spark_chars)

    def test_percentage_change_shown(self):
        result = make_sparkline([100.0, 110.0])
        assert "%" in result

    def test_respects_width(self):
        values = list(range(100))
        result = make_sparkline(values, width=10)
        # Strip markup to count actual sparkline characters
        import re
        cleaned = re.sub(r"\[.*?\]", "", result)
        spark_chars = "▁▂▃▄▅▆▇█"
        spark_part = "".join(c for c in cleaned if c in spark_chars)
        assert len(spark_part) == 10

    def test_flat_line_no_crash(self):
        result = make_sparkline([100.0, 100.0, 100.0])
        # All same value — range is 0; should not raise ZeroDivisionError
        assert "%" in result

    def test_custom_width_used(self):
        result = make_sparkline([1.0, 2.0, 3.0], width=3)
        assert "[dim]No data[/dim]" not in result


class TestSafeFloat:
    def test_none_returns_none(self):
        assert safe_float(None) is None

    def test_int_converts(self):
        assert safe_float(5) == pytest.approx(5.0)

    def test_float_passthrough(self):
        assert safe_float(3.14) == pytest.approx(3.14)

    def test_list_takes_first(self):
        assert safe_float([42.0, 99.0]) == pytest.approx(42.0)

    def test_empty_list_returns_none(self):
        assert safe_float([]) is None

    def test_string_converts(self):
        assert safe_float("1.5") == pytest.approx(1.5)

    def test_non_numeric_string_returns_none(self):
        assert safe_float("abc") is None
