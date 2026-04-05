"""Unit tests for the fund analysis engine — mocked, no network calls."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from finscope.fund_analysis.engine import (
    _aum_rating,
    _consistency_score,
    _expense_rating,
    _nav_list_to_df,
    _overall_rating,
    _rolling_returns,
    analyze_global_fund,
    analyze_india_fund,
)
from finscope.fund_analysis.models import FundAnalysis, FundRisk


# ── fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def prices_1y() -> pd.DataFrame:
    dates = pd.date_range("2023-01-01", periods=252, freq="B")
    close = 100 * (1 + np.random.default_rng(42).normal(0.0004, 0.010, 252)).cumprod()
    return pd.DataFrame({"Close": close}, index=dates)


@pytest.fixture
def prices_5y() -> pd.DataFrame:
    dates = pd.date_range("2019-01-01", periods=1260, freq="B")
    close = 100 * (1 + np.random.default_rng(7).normal(0.0003, 0.009, 1260)).cumprod()
    return pd.DataFrame({"Close": close}, index=dates)


@pytest.fixture
def nav_data_1y() -> list[dict]:
    """Simulate 365 days of MFAPI NAV data (newest first)."""
    dates = pd.date_range("2024-01-01", periods=365, freq="D")
    navs  = 50 * (1 + np.random.default_rng(1).normal(0.0003, 0.006, 365)).cumprod()
    return [
        {"date": d.strftime("%d-%m-%Y"), "nav": f"{v:.4f}"}
        for d, v in zip(reversed(dates), reversed(navs))
    ]


@pytest.fixture
def india_meta() -> dict:
    return {
        "scheme_name": "SBI Small Cap Fund - Direct Plan",
        "fund_house":  "SBI Mutual Fund",
        "scheme_category": "Equity: Small Cap",
        "scheme_type": "Open Ended Schemes",
    }


# ── _nav_list_to_df ───────────────────────────────────────────────────────────

class TestNavListToDf:
    def test_converts_correctly(self, nav_data_1y):
        df = _nav_list_to_df(nav_data_1y)
        assert not df.empty
        assert "Close" in df.columns
        assert df.index.is_monotonic_increasing   # oldest first after sort

    def test_empty_input(self):
        assert _nav_list_to_df([]).empty

    def test_bad_entries_skipped(self):
        bad_data = [
            {"date": "01-01-2024", "nav": "50.0"},
            {"date": "bad-date",   "nav": "N/A"},
            {"date": "02-01-2024", "nav": "51.0"},
        ]
        df = _nav_list_to_df(bad_data)
        assert len(df) == 2


# ── _rolling_returns ──────────────────────────────────────────────────────────

class TestRollingReturns:
    def test_1y_available_for_252_days(self, prices_1y):
        r = _rolling_returns(prices_1y)
        assert "1Y" in r and r["1Y"] is not None

    def test_5y_available_for_1260_days(self, prices_5y):
        r = _rolling_returns(prices_5y)
        assert "5Y" in r and r["5Y"] is not None

    def test_3y_none_for_1y_data(self, prices_1y):
        r = _rolling_returns(prices_1y)
        assert r.get("3Y") is None

    def test_empty_df(self):
        assert _rolling_returns(pd.DataFrame()) == {}


# ── _consistency_score ────────────────────────────────────────────────────────

class TestConsistencyScore:
    def test_returns_none_for_short_history(self, prices_1y):
        # 252 days = exactly 1 year, need > 252 for rolling windows
        c = _consistency_score(prices_1y)
        assert c is None

    def test_returns_float_for_multi_year(self, prices_5y):
        c = _consistency_score(prices_5y)
        assert c is not None
        assert 0.0 <= c <= 1.0

    def test_always_rising_fund_scores_high(self):
        dates = pd.date_range("2018-01-01", periods=1260, freq="B")
        close = np.arange(100, 100 + 1260, 1, dtype=float)
        df = pd.DataFrame({"Close": close}, index=dates)
        c = _consistency_score(df)
        assert c == pytest.approx(1.0)


# ── _expense_rating ───────────────────────────────────────────────────────────

class TestExpenseRating:
    def test_etf_excellent(self):
        assert _expense_rating(0.0003, "Global") == "Excellent"

    def test_etf_high(self):
        assert _expense_rating(0.02, "Global") == "Very High"

    def test_india_excellent(self):
        assert _expense_rating(0.003, "India") == "Excellent"

    def test_india_high(self):
        assert _expense_rating(0.03, "India") == "Very High"

    def test_none_returns_na(self):
        assert _expense_rating(None, "Global") == "N/A"


# ── _aum_rating ───────────────────────────────────────────────────────────────

class TestAumRating:
    def test_large(self):  assert "Large"  in _aum_rating(50e9)
    def test_medium(self): assert "Medium" in _aum_rating(5e9)
    def test_small(self):  assert "Small"  in _aum_rating(500e6)
    def test_micro(self):  assert "Micro"  in _aum_rating(50e6)
    def test_none(self):   assert _aum_rating(None) == "N/A"


# ── _overall_rating ───────────────────────────────────────────────────────────

class TestOverallRating:
    def test_strong_fund(self):
        rolling = {"1Y": 0.25, "3Y": 0.18}
        rating, h, c = _overall_rating(rolling, "Excellent", 1.5, 0.85)
        assert rating in ("Strong", "Good")
        assert len(h) > 0

    def test_weak_fund(self):
        rolling = {"1Y": -0.15, "3Y": -0.08}
        rating, h, c = _overall_rating(rolling, "Very High", -0.3, 0.40)
        assert rating in ("Below Average", "Weak")
        assert len(c) > 0


# ── analyze_india_fund ────────────────────────────────────────────────────────

class TestAnalyzeIndiaFund:
    def test_returns_tuple(self, nav_data_1y, india_meta):
        risk, analysis = analyze_india_fund(nav_data_1y, india_meta)
        assert isinstance(risk, FundRisk)
        assert isinstance(analysis, FundAnalysis)

    def test_name_from_meta(self, nav_data_1y, india_meta):
        risk, analysis = analyze_india_fund(nav_data_1y, india_meta)
        assert "SBI" in risk.name
        assert analysis.fund_house == "SBI Mutual Fund"

    def test_fund_type_india(self, nav_data_1y, india_meta):
        risk, _ = analyze_india_fund(nav_data_1y, india_meta)
        assert risk.fund_type == "India"

    def test_empty_nav_data(self, india_meta):
        risk, analysis = analyze_india_fund([], india_meta)
        assert risk.risk_level == "N/A"

    def test_risk_level_set(self, nav_data_1y, india_meta):
        risk, _ = analyze_india_fund(nav_data_1y, india_meta)
        assert risk.risk_level in ("Low", "Moderate", "High", "Very High", "N/A")

    def test_rolling_returns_computed(self, nav_data_1y, india_meta):
        _, analysis = analyze_india_fund(nav_data_1y, india_meta)
        assert "1Y" in analysis.rolling_returns


# ── analyze_global_fund ───────────────────────────────────────────────────────

class TestAnalyzeGlobalFund:
    def test_returns_tuple(self, prices_1y):
        mock_fund = MagicMock()
        mock_fund.info = {
            "longName": "Vanguard S&P 500 ETF",
            "annualReportExpenseRatio": 0.0003,
            "totalAssets": 400e9,
            "beta": 1.0,
            "category": "Large Blend",
            "fundFamily": "Vanguard",
            "fiftyTwoWeekHigh": 450.0,
        }
        mock_fund._service.get_price_history.return_value = prices_1y

        with patch("finscope.fund", return_value=mock_fund):
            risk, analysis = analyze_global_fund("VOO", fund=mock_fund)

        assert isinstance(risk, FundRisk)
        assert isinstance(analysis, FundAnalysis)
        assert risk.fund_type == "Global"
        assert analysis.expense_rating == "Excellent"
        assert "Large" in analysis.aum_rating

    def test_empty_prices_graceful(self):
        mock_fund = MagicMock()
        mock_fund.info = {"longName": "Test ETF"}
        mock_fund._service.get_price_history.return_value = pd.DataFrame()

        risk, analysis = analyze_global_fund("TEST", fund=mock_fund)
        assert risk.risk_level == "N/A"


# ── Fund class methods ────────────────────────────────────────────────────────

class TestFundMethods:
    def test_fund_risk_method(self, prices_1y):
        from finscope.stock import Fund
        mock_svc = MagicMock()
        mock_svc.get_fund_info.return_value = {"longName": "Test ETF"}
        mock_svc.get_price_history.return_value = prices_1y
        f = Fund("SPY", service=mock_svc)

        with patch("finscope.fund_analysis.analyze_global_fund") as mock_ag:
            mock_ag.return_value = (FundRisk(name="SPY ETF"), FundAnalysis(name="SPY ETF"))
            result = f.risk()

        assert isinstance(result, FundRisk)

    def test_fund_analyze_method(self, prices_1y):
        from finscope.stock import Fund
        mock_svc = MagicMock()
        mock_svc.get_fund_info.return_value = {"longName": "Test ETF"}
        f = Fund("SPY", service=mock_svc)

        with patch("finscope.fund_analysis.analyze_global_fund") as mock_ag:
            mock_ag.return_value = (FundRisk(name="SPY ETF"), FundAnalysis(name="SPY ETF"))
            result = f.analyze()

        assert isinstance(result, FundAnalysis)
