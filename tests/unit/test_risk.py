"""Unit tests for the risk engine — all mocked, no network calls."""

from __future__ import annotations

import math
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from finscope.risk.engine import (
    _compute_downside,
    _compute_fundamental_risk,
    _compute_market_risk,
    _compute_risk_adjusted,
    _compute_volatility,
    _composite_score,
    _daily_returns,
)
from finscope.risk.models import (
    DownsideRisk,
    FundamentalRisk,
    MarketRisk,
    RiskAdjustedMetrics,
    StockRisk,
    VolatilityMetrics,
)


# ── fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def stable_prices() -> pd.DataFrame:
    """Simulate a low-volatility stock rising ~10% over a year."""
    dates = pd.date_range("2023-01-01", periods=252, freq="B")
    close = 100 * (1 + np.random.default_rng(42).normal(0.0004, 0.008, 252)).cumprod()
    return pd.DataFrame({"Close": close}, index=dates)


@pytest.fixture
def volatile_prices() -> pd.DataFrame:
    """Simulate a high-volatility stock with a big drawdown mid-year."""
    dates = pd.date_range("2023-01-01", periods=252, freq="B")
    rng = np.random.default_rng(7)
    returns = rng.normal(0.0002, 0.025, 252)  # 40%+ annualised vol
    returns[100:130] = -0.03                  # prolonged drawdown period
    close = 100 * (1 + returns).cumprod()
    return pd.DataFrame({"Close": close}, index=dates)


@pytest.fixture
def stable_returns(stable_prices):
    return _daily_returns(stable_prices)


@pytest.fixture
def volatile_returns(volatile_prices):
    return _daily_returns(volatile_prices)


@pytest.fixture
def healthy_info() -> dict:
    return {
        "beta": 0.9,
        "debtToEquity": 50.0,
        "currentRatio": 2.0,
        "ebit": 10_000_000,
        "interestExpense": 500_000,
        "operatingCashflow": 8_000_000,
        "netIncomeToCommon": 6_000_000,
        "totalAssets": 50_000_000,
        "totalCurrentAssets": 20_000_000,
        "totalCurrentLiabilities": 10_000_000,
        "retainedEarnings": 15_000_000,
        "ebitda": 12_000_000,
        "marketCap": 100_000_000,
        "totalDebt": 25_000_000,
        "totalRevenue": 40_000_000,
        "currentPrice": 150.0,
        "fiftyTwoWeekHigh": 180.0,
    }


@pytest.fixture
def risky_info() -> dict:
    return {
        "beta": 2.1,
        "debtToEquity": 350.0,
        "currentRatio": 0.7,
        "ebit": 1_000_000,
        "interestExpense": 900_000,
        "operatingCashflow": -2_000_000,
        "netIncomeToCommon": 500_000,
        "totalAssets": 5_000_000,
        "currentPrice": 20.0,
        "fiftyTwoWeekHigh": 45.0,
    }


# ── _compute_volatility ───────────────────────────────────────────────────────

class TestVolatility:
    def test_annual_vol_computed(self, stable_returns):
        v = _compute_volatility(stable_returns)
        assert v.annual_vol is not None
        assert v.annual_vol == pytest.approx(stable_returns.std() * math.sqrt(252), rel=0.01)

    def test_interpretation_low(self, stable_returns):
        v = _compute_volatility(stable_returns)
        assert v.interpretation in ("Low", "Moderate")

    def test_interpretation_high(self, volatile_returns):
        v = _compute_volatility(volatile_returns)
        assert v.interpretation in ("High", "Very High")

    def test_rolling_windows(self, stable_returns):
        v = _compute_volatility(stable_returns)
        assert v.vol_30d is not None
        assert v.vol_90d is not None

    def test_skewness_and_kurtosis(self, stable_returns):
        v = _compute_volatility(stable_returns)
        assert v.skewness is not None
        assert v.kurtosis is not None

    def test_empty_returns(self):
        v = _compute_volatility(pd.Series(dtype=float))
        assert v.annual_vol is None
        assert v.interpretation == "N/A"


# ── _compute_downside ─────────────────────────────────────────────────────────

class TestDownside:
    def test_var_95_negative(self, stable_returns, stable_prices, healthy_info):
        d = _compute_downside(stable_returns, stable_prices, healthy_info)
        assert d.var_95 is not None
        assert d.var_95 < 0

    def test_var_99_worse_than_95(self, volatile_returns, volatile_prices, risky_info):
        d = _compute_downside(volatile_returns, volatile_prices, risky_info)
        assert d.var_99 < d.var_95

    def test_cvar_worse_than_var(self, volatile_returns, volatile_prices, risky_info):
        d = _compute_downside(volatile_returns, volatile_prices, risky_info)
        if d.cvar_95 is not None:
            assert d.cvar_95 <= d.var_95

    def test_max_drawdown_negative(self, volatile_returns, volatile_prices, risky_info):
        d = _compute_downside(volatile_returns, volatile_prices, risky_info)
        assert d.max_drawdown is not None
        assert d.max_drawdown < 0

    def test_current_drawdown_computed(self, stable_returns, stable_prices, healthy_info):
        d = _compute_downside(stable_returns, stable_prices, healthy_info)
        assert d.current_drawdown is not None
        assert d.current_drawdown <= 0

    def test_empty_returns(self):
        d = _compute_downside(pd.Series(dtype=float), pd.DataFrame(), {})
        assert d.var_95 is None


# ── _compute_risk_adjusted ────────────────────────────────────────────────────

class TestRiskAdjusted:
    def test_sharpe_computed(self, stable_returns):
        vol = _compute_volatility(stable_returns)
        dd = DownsideRisk(max_drawdown=-0.10)
        ra = _compute_risk_adjusted(stable_returns, dd, vol)
        assert ra.sharpe_ratio is not None

    def test_sortino_computed(self, stable_returns):
        vol = _compute_volatility(stable_returns)
        dd = DownsideRisk(max_drawdown=-0.10)
        ra = _compute_risk_adjusted(stable_returns, dd, vol)
        assert ra.sortino_ratio is not None

    def test_calmar_positive_for_positive_return(self, stable_returns):
        vol = _compute_volatility(stable_returns)
        dd = DownsideRisk(max_drawdown=-0.15)
        ra = _compute_risk_adjusted(stable_returns, dd, vol)
        if ra.calmar_ratio is not None and ra.annual_return and ra.annual_return > 0:
            assert ra.calmar_ratio > 0

    def test_interpretation_set(self, stable_returns):
        vol = _compute_volatility(stable_returns)
        dd = DownsideRisk(max_drawdown=-0.10)
        ra = _compute_risk_adjusted(stable_returns, dd, vol)
        assert ra.interpretation in ("Excellent", "Good", "Adequate", "Below Average", "Poor", "N/A")


# ── _compute_market_risk ──────────────────────────────────────────────────────

class TestMarketRisk:
    def test_beta_from_info(self, stable_returns, healthy_info):
        m = _compute_market_risk(stable_returns, healthy_info, None)
        assert m.beta == 0.9

    def test_beta_calculated_from_returns(self, stable_returns, stable_prices, healthy_info):
        market_returns = stable_returns * 0.8 + pd.Series(
            np.random.default_rng(1).normal(0, 0.001, len(stable_returns)),
            index=stable_returns.index,
        )
        m = _compute_market_risk(stable_returns, healthy_info, market_returns)
        assert m.beta_calculated is not None
        assert m.r_squared is not None
        assert 0.0 <= m.r_squared <= 1.0

    def test_interpretation_set(self, stable_returns, healthy_info):
        m = _compute_market_risk(stable_returns, healthy_info, None)
        assert m.interpretation != "N/A"

    def test_high_beta_aggressive(self, stable_returns, risky_info):
        m = _compute_market_risk(stable_returns, risky_info, None)
        assert "Aggressive" in m.interpretation or "Aggressive" in m.interpretation


# ── _compute_fundamental_risk ─────────────────────────────────────────────────

class TestFundamentalRisk:
    def test_healthy_company_low_risk(self, healthy_info):
        f = _compute_fundamental_risk(healthy_info)
        assert f.interpretation in ("Low Risk", "Moderate Risk")

    def test_risky_company_high_risk(self, risky_info):
        f = _compute_fundamental_risk(risky_info)
        assert f.interpretation in ("High Risk", "Very High Risk")

    def test_earnings_quality_good(self, healthy_info):
        f = _compute_fundamental_risk(healthy_info)
        assert f.earnings_quality == "Good"

    def test_earnings_quality_weak(self, risky_info):
        f = _compute_fundamental_risk(risky_info)
        assert f.earnings_quality == "Weak"

    def test_interest_coverage_computed(self, healthy_info):
        f = _compute_fundamental_risk(healthy_info)
        assert f.interest_coverage == pytest.approx(20.0, rel=0.01)


# ── _composite_score ──────────────────────────────────────────────────────────

class TestCompositeScore:
    def test_low_risk_score(self):
        vol = VolatilityMetrics(annual_vol=0.10, interpretation="Low")
        dd  = DownsideRisk(max_drawdown=-0.08, var_95=-0.01)
        ra  = RiskAdjustedMetrics(sharpe_ratio=2.0)
        mk  = MarketRisk(beta=0.5)
        fu  = FundamentalRisk(debt_to_equity=40, current_ratio=2.5,
                              interest_coverage=10, altman_zone="Safe",
                              earnings_quality="Good")
        score, level, factors, positives = _composite_score(vol, dd, ra, mk, fu)
        assert score < 30
        assert level == "Low"
        assert len(positives) > 0

    def test_high_risk_score(self):
        vol = VolatilityMetrics(annual_vol=0.65, interpretation="Very High")
        dd  = DownsideRisk(max_drawdown=-0.65, var_95=-0.06)
        ra  = RiskAdjustedMetrics(sharpe_ratio=-0.5)
        mk  = MarketRisk(beta=2.5)
        fu  = FundamentalRisk(debt_to_equity=400, current_ratio=0.6,
                              interest_coverage=1.2, altman_zone="Distress",
                              earnings_quality="Weak")
        score, level, factors, positives = _composite_score(vol, dd, ra, mk, fu)
        assert score >= 60
        assert level in ("High", "Very High")
        assert len(factors) > 0

    def test_score_clamped_at_100(self):
        vol = VolatilityMetrics(annual_vol=1.0)
        dd  = DownsideRisk(max_drawdown=-0.9, var_95=-0.10)
        ra  = RiskAdjustedMetrics(sharpe_ratio=-2.0)
        mk  = MarketRisk(beta=3.0)
        fu  = FundamentalRisk(debt_to_equity=500, current_ratio=0.3,
                              interest_coverage=0.5, altman_zone="Distress",
                              earnings_quality="Weak")
        score, _, _, _ = _composite_score(vol, dd, ra, mk, fu)
        assert score <= 100


# ── compute_risk (integration, mocked) ───────────────────────────────────────

class TestComputeRisk:
    def test_returns_stock_risk(self, stable_prices, healthy_info):
        mock_stock = MagicMock()
        mock_stock.info = healthy_info
        mock_stock.price_history.return_value = stable_prices

        from finscope.risk.engine import compute_risk
        result = compute_risk("AAPL", stock=mock_stock)

        assert isinstance(result, StockRisk)
        assert result.symbol == "AAPL"
        assert result.risk_level in ("Low", "Moderate", "High", "Very High")
        assert result.risk_score is not None

    def test_empty_prices_returns_bare_result(self, healthy_info):
        mock_stock = MagicMock()
        mock_stock.info = healthy_info
        mock_stock.price_history.return_value = pd.DataFrame()

        from finscope.risk.engine import compute_risk
        result = compute_risk("AAPL", stock=mock_stock)

        assert result.risk_level == "N/A"


# ── Stock.risk() method ───────────────────────────────────────────────────────

class TestStockRiskMethod:
    def test_stock_risk_method(self, stable_prices, healthy_info):
        from finscope.stock import Stock
        mock_svc = MagicMock()
        mock_svc.get_info.return_value = healthy_info
        s = Stock("AAPL", service=mock_svc)

        with patch("finscope.risk.compute_risk") as mock_cr:
            mock_cr.return_value = StockRisk(symbol="AAPL")
            result = s.risk()

        mock_cr.assert_called_once_with("AAPL", period="1y", stock=s)
        assert isinstance(result, StockRisk)


# ── CLI dispatch ──────────────────────────────────────────────────────────────

class TestCLIRisk:
    def test_risk_dispatch(self):
        from finscope.cli import _build_parser, _dispatch
        ns = _build_parser().parse_args(["AAPL", "risk"])
        with patch("finscope.cli.cmd_risk") as mock:
            _dispatch(ns)
        mock.assert_called_once_with("AAPL", "1mo")  # default period from parser
