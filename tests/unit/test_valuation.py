"""Unit tests for the valuation engine.

All tests use mocked data — no real network calls.
"""

from __future__ import annotations

import math
from unittest.mock import MagicMock, patch

import pytest

from finscope.valuation.engine import (
    _altman_z_score,
    _dcf_valuation,
    _graham_number,
    _peg_fair_value,
    _piotroski_score,
    _relative_valuation,
    _safe_div,
    _safe_get,
    _pct_diff,
    _signal_from_margin,
)
from finscope.valuation.models import (
    AltmanResult,
    DCFResult,
    GrahamResult,
    PEGResult,
    PiotroskiResult,
    RelativeResult,
    StockValuation,
)


# ── Helper tests ──────────────────────────────────────────────────────────────


class TestHelpers:
    def test_safe_get_first_key(self):
        assert _safe_get({"a": 1.0, "b": 2.0}, "a", "b") == 1.0

    def test_safe_get_fallback(self):
        assert _safe_get({"b": 2.0}, "a", "b") == 2.0

    def test_safe_get_missing(self):
        assert _safe_get({}, "a") is None

    def test_safe_get_non_numeric(self):
        assert _safe_get({"a": "hello"}, "a") is None

    def test_safe_div_normal(self):
        assert _safe_div(10.0, 2.0) == pytest.approx(5.0)

    def test_safe_div_by_zero(self):
        assert _safe_div(10.0, 0.0) is None

    def test_safe_div_none(self):
        assert _safe_div(None, 2.0) is None
        assert _safe_div(10.0, None) is None

    def test_pct_diff(self):
        assert _pct_diff(100.0, 120.0) == pytest.approx(20.0)
        assert _pct_diff(100.0, 80.0) == pytest.approx(-20.0)

    def test_pct_diff_zero_current(self):
        assert _pct_diff(0.0, 100.0) is None

    def test_signal_from_margin(self):
        assert _signal_from_margin(20.0) == "Undervalued"
        assert _signal_from_margin(-20.0) == "Overvalued"
        assert _signal_from_margin(5.0) == "Fairly Valued"
        assert _signal_from_margin(None) == "N/A"


# ── Graham Number ─────────────────────────────────────────────────────────────


class TestGrahamNumber:
    def test_positive_eps_and_bvps(self):
        info = {"trailingEps": 6.0, "bookValue": 4.0, "currentPrice": 10.0}
        result = _graham_number(info)
        expected = math.sqrt(22.5 * 6.0 * 4.0)
        assert result.intrinsic == pytest.approx(expected)
        assert result.calculable is True

    def test_negative_eps_not_calculable(self):
        info = {"trailingEps": -2.0, "bookValue": 10.0, "currentPrice": 50.0}
        result = _graham_number(info)
        assert result.calculable is False
        assert result.signal == "N/A"

    def test_missing_data(self):
        result = _graham_number({})
        assert result.calculable is False

    def test_undervalued_signal(self):
        # Intrinsic > price by >15%
        info = {"trailingEps": 10.0, "bookValue": 20.0, "currentPrice": 30.0}
        result = _graham_number(info)
        # sqrt(22.5 * 10 * 20) = sqrt(4500) ≈ 67.08
        assert result.signal == "Undervalued"

    def test_overvalued_signal(self):
        info = {"trailingEps": 1.0, "bookValue": 1.0, "currentPrice": 100.0}
        result = _graham_number(info)
        # sqrt(22.5 * 1 * 1) ≈ 4.74 << 100
        assert result.signal == "Overvalued"

    def test_margin_of_safety_calculated(self):
        info = {"trailingEps": 6.0, "bookValue": 4.0, "currentPrice": 10.0}
        result = _graham_number(info)
        assert result.margin_of_safety_pct is not None


# ── DCF ───────────────────────────────────────────────────────────────────────


class TestDCF:
    def test_basic_dcf(self):
        info = {
            "freeCashflow": 100_000_000_000,
            "revenueGrowth": 0.10,
            "earningsGrowth": 0.12,
            "beta": 1.2,
            "sharesOutstanding": 15_000_000_000,
            "currentPrice": 175.0,
        }
        result = _dcf_valuation(info, None)
        assert result.calculable is True
        assert result.intrinsic_per_share > 0
        assert result.discount_rate is not None

    def test_negative_fcf_not_calculable(self):
        info = {
            "freeCashflow": -50_000_000,
            "revenueGrowth": 0.10,
            "sharesOutstanding": 1_000_000,
            "currentPrice": 50.0,
        }
        result = _dcf_valuation(info, None)
        assert result.calculable is False

    def test_missing_growth_from_financials(self, sample_financials_df):
        info = {
            "freeCashflow": 100_000_000,
            "sharesOutstanding": 10_000_000,
            "currentPrice": 50.0,
            "beta": 1.0,
        }
        result = _dcf_valuation(info, sample_financials_df)
        # Should try to compute growth from financials
        assert result.growth_rate is not None or result.calculable is False

    def test_missing_all_data(self):
        result = _dcf_valuation({}, None)
        assert result.calculable is False

    def test_growth_capped(self):
        info = {
            "freeCashflow": 100_000_000,
            "revenueGrowth": 0.50,  # 50% — should be capped at 30%
            "earningsGrowth": 0.60,
            "sharesOutstanding": 1_000_000,
            "currentPrice": 50.0,
            "beta": 1.0,
        }
        result = _dcf_valuation(info, None)
        assert result.calculable is True


# ── PEG ───────────────────────────────────────────────────────────────────────


class TestPEG:
    def test_basic_peg(self):
        info = {
            "pegRatio": 1.5,
            "trailingPE": 30.0,
            "trailingEps": 6.0,
            "earningsGrowth": 0.20,  # 20%
            "currentPrice": 180.0,
        }
        result = _peg_fair_value(info)
        # Fair price = 20% * 6.0 = 120
        assert result.fair_price == pytest.approx(120.0)
        assert result.calculable is True

    def test_peg_below_1_is_undervalued(self):
        info = {"pegRatio": 0.7, "trailingEps": -1.0}
        result = _peg_fair_value(info)
        assert result.signal == "Undervalued"

    def test_peg_above_1_5_is_overvalued(self):
        info = {"pegRatio": 2.0, "trailingEps": -1.0}
        result = _peg_fair_value(info)
        assert result.signal == "Overvalued"

    def test_missing_data(self):
        result = _peg_fair_value({})
        assert result.calculable is False

    def test_negative_eps_uses_peg_fallback(self):
        info = {"pegRatio": 0.6, "trailingEps": -5.0}
        result = _peg_fair_value(info)
        assert result.signal == "Undervalued"


# ── Relative ──────────────────────────────────────────────────────────────────


class TestRelative:
    def test_basic_relative(self, apple_info):
        result = _relative_valuation(apple_info)
        assert result.pe_current == pytest.approx(28.5)
        assert result.calculable is True

    def test_low_pe_bullish(self):
        info = {"trailingPE": 8.0, "currentPrice": 50.0, "twoHundredDayAverage": 55.0}
        result = _relative_valuation(info)
        # Low PE (bullish) + price below 200D (bullish) → Undervalued
        assert result.signal == "Undervalued"

    def test_high_pe_bearish(self):
        info = {"trailingPE": 50.0, "currentPrice": 200.0, "twoHundredDayAverage": 195.0}
        result = _relative_valuation(info)
        # High PE (bearish) + price near 200D (<10% diff, neutral) → Overvalued wins
        assert result.signal == "Overvalued"

    def test_missing_data(self):
        result = _relative_valuation({})
        assert result.signal == "N/A"


# ── Piotroski ─────────────────────────────────────────────────────────────────


class TestPiotroski:
    def test_strong_company(self):
        info = {
            "returnOnAssets": 0.15,
            "operatingCashflow": 100_000_000,
            "netIncomeToCommon": 80_000_000,
            "debtToEquity": 50.0,
            "currentRatio": 1.5,
            "sharesOutstanding": 1_000_000,
            "floatShares": 950_000,
            "grossMargins": 0.45,
            "totalRevenue": 500_000_000,
            "totalAssets": 800_000_000,
        }
        result = _piotroski_score(info, None, None)
        assert result.score >= 7
        assert result.strength == "Strong"

    def test_weak_company(self):
        info = {
            "returnOnAssets": -0.05,
            "operatingCashflow": -10_000_000,
            "debtToEquity": 300.0,
            "currentRatio": 0.5,
            "grossMargins": 0.10,
        }
        result = _piotroski_score(info, None, None)
        assert result.score <= 3
        assert result.strength == "Weak"

    def test_score_range(self):
        info = {"returnOnAssets": 0.10, "operatingCashflow": 50_000_000}
        result = _piotroski_score(info, None, None)
        assert 0 <= result.score <= 9

    def test_details_populated(self):
        info = {"returnOnAssets": 0.10}
        result = _piotroski_score(info, None, None)
        assert "Positive ROA" in result.details

    def test_empty_info(self):
        result = _piotroski_score({}, None, None)
        assert result.score >= 0


# ── Altman Z-Score ────────────────────────────────────────────────────────────


class TestAltman:
    def test_safe_zone(self):
        info = {
            "totalAssets": 1_000_000,
            "totalCurrentAssets": 500_000,
            "totalCurrentLiabilities": 200_000,
            "retainedEarnings": 400_000,
            "ebitda": 200_000,
            "marketCap": 5_000_000,
            "totalDebt": 300_000,
            "totalRevenue": 800_000,
        }
        result = _altman_z_score(info)
        assert result.calculable is True
        assert result.z_score > 2.99
        assert result.zone == "Safe"

    def test_distress_zone(self):
        info = {
            "totalAssets": 1_000_000,
            "totalCurrentAssets": 100_000,
            "totalCurrentLiabilities": 500_000,
            "retainedEarnings": -200_000,
            "ebitda": 10_000,
            "marketCap": 200_000,
            "totalDebt": 800_000,
            "totalRevenue": 300_000,
        }
        result = _altman_z_score(info)
        assert result.calculable is True
        assert result.z_score < 1.81
        assert result.zone == "Distress"

    def test_missing_total_assets(self):
        result = _altman_z_score({})
        assert result.calculable is False

    def test_components_populated(self):
        info = {
            "totalAssets": 1_000_000,
            "totalCurrentAssets": 500_000,
            "totalCurrentLiabilities": 200_000,
            "retainedEarnings": 400_000,
            "ebitda": 200_000,
            "marketCap": 5_000_000,
            "totalDebt": 300_000,
            "totalRevenue": 800_000,
        }
        result = _altman_z_score(info)
        assert "A (WC/TA)" in result.components
        assert "E (Rev/TA)" in result.components


# ── Composite Valuation Model ─────────────────────────────────────────────────


class TestStockValuationModel:
    def test_default_construction(self):
        v = StockValuation(symbol="AAPL")
        assert v.symbol == "AAPL"
        assert v.verdict == "N/A"
        assert v.graham.calculable is False

    def test_repr_with_margin(self):
        v = StockValuation(symbol="AAPL", current_price=175.0,
                           verdict="Undervalued", confidence="High",
                           margin_of_safety=15.0)
        r = repr(v)
        assert "AAPL" in r
        assert "Undervalued" in r

    def test_repr_without_margin(self):
        v = StockValuation(symbol="AAPL")
        r = repr(v)
        assert "AAPL" in r


# ── Engine integration (mocked Stock) ─────────────────────────────────────────


class TestValuateFunction:
    def test_valuate_returns_stock_valuation(self, apple_info, sample_financials_df):
        mock_stock = MagicMock()
        mock_stock.info = apple_info
        mock_stock.financials = sample_financials_df
        mock_stock.balance_sheet = sample_financials_df

        from finscope.valuation.engine import valuate
        result = valuate("AAPL", stock=mock_stock)

        assert isinstance(result, StockValuation)
        assert result.symbol == "AAPL"
        assert result.current_price is not None

    def test_verdict_is_set(self, apple_info, sample_financials_df):
        mock_stock = MagicMock()
        mock_stock.info = apple_info
        mock_stock.financials = sample_financials_df
        mock_stock.balance_sheet = sample_financials_df

        from finscope.valuation.engine import valuate
        result = valuate("AAPL", stock=mock_stock)

        assert result.verdict in {"Undervalued", "Fairly Valued", "Overvalued", "N/A"}
        assert result.confidence in {"High", "Medium", "Low"}


# ── CLI dispatch test ─────────────────────────────────────────────────────────


class TestCLIValuate:
    def test_valuate_dispatch(self):
        from finscope.cli import _build_parser, _dispatch
        ns = _build_parser().parse_args(["AAPL", "valuate"])
        with patch("finscope.cli.cmd_valuate") as mock:
            _dispatch(ns)
        mock.assert_called_once_with("AAPL")

    def test_stock_valuate_method(self, apple_info):
        from finscope.stock import Stock
        mock_svc = MagicMock()
        mock_svc.get_info.return_value = apple_info
        s = Stock("AAPL", service=mock_svc)

        mock_stock_for_engine = MagicMock()
        mock_stock_for_engine.info = apple_info
        mock_stock_for_engine.financials = None
        mock_stock_for_engine.balance_sheet = None

        with patch("finscope.valuation.valuate") as mock_val:
            mock_val.return_value = StockValuation(symbol="AAPL")
            v = s.valuate()
        assert isinstance(v, StockValuation)
