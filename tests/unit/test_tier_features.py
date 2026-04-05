"""Tests for portfolio tracker, watchlist, dividends, earnings, and peers."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from finscope.portfolio import Portfolio, Holding, PortfolioSummary
from finscope.watchlist import Watchlist


# ── Portfolio ─────────────────────────────────────────────────────────────────

class TestPortfolio:
    def test_add_and_list(self, tmp_path):
        p = Portfolio(tmp_path / "port.json")
        p.add("AAPL", 50, 142.50)
        assert "AAPL" in p.symbols

    def test_add_averages_cost(self, tmp_path):
        p = Portfolio(tmp_path / "port.json")
        p.add("AAPL", 50, 100.00)
        p.add("AAPL", 50, 200.00)
        data = json.loads((tmp_path / "port.json").read_text())
        assert data["holdings"]["AAPL"]["shares"] == 100
        assert data["holdings"]["AAPL"]["avg_cost"] == 150.0

    def test_remove(self, tmp_path):
        p = Portfolio(tmp_path / "port.json")
        p.add("AAPL", 10, 100)
        assert p.remove("AAPL") is True
        assert p.is_empty

    def test_remove_missing(self, tmp_path):
        p = Portfolio(tmp_path / "port.json")
        assert p.remove("NOPE") is False

    def test_clear(self, tmp_path):
        p = Portfolio(tmp_path / "port.json")
        p.add("AAPL", 10, 100)
        p.add("MSFT", 5, 200)
        p.clear()
        assert p.is_empty

    def test_persistence(self, tmp_path):
        path = tmp_path / "port.json"
        p = Portfolio(path)
        p.add("AAPL", 50, 142.50)
        p2 = Portfolio(path)
        assert "AAPL" in p2.symbols

    def test_summary_empty(self, tmp_path):
        p = Portfolio(tmp_path / "port.json")
        s = p.summary()
        assert s.num_holdings == 0

    def test_summary_with_stock(self, tmp_path):
        p = Portfolio(tmp_path / "port.json")
        p.add("AAPL", 10, 100.0)

        mock_stock = MagicMock()
        mock_stock.info = {
            "currentPrice": 150.0, "shortName": "Apple",
            "sector": "Technology", "regularMarketChangePercent": 1.0,
            "beta": 1.2, "trailingPE": 28.0,
        }
        with patch("finscope.stock", return_value=mock_stock):
            s = p.summary()

        assert s.num_holdings == 1
        assert s.total_value == pytest.approx(1500.0)
        assert s.total_pnl == pytest.approx(500.0)


# ── Holding ───────────────────────────────────────────────────────────────────

class TestHolding:
    def test_cost_basis(self):
        h = Holding(symbol="AAPL", shares=10, avg_cost=100)
        assert h.cost_basis == 1000

    def test_pnl(self):
        h = Holding(symbol="AAPL", shares=10, avg_cost=100, current_price=150)
        assert h.pnl == 500
        assert h.pnl_pct == pytest.approx(50.0)

    def test_pnl_none_without_price(self):
        h = Holding(symbol="AAPL", shares=10, avg_cost=100)
        assert h.pnl is None


# ── Watchlist ─────────────────────────────────────────────────────────────────

class TestWatchlist:
    def test_add_and_list(self, tmp_path):
        w = Watchlist(tmp_path / "watch.json")
        w.add("AAPL", "MSFT")
        assert w.symbols == ["AAPL", "MSFT"]

    def test_no_duplicates(self, tmp_path):
        w = Watchlist(tmp_path / "watch.json")
        w.add("AAPL", "AAPL", "AAPL")
        assert w.symbols == ["AAPL"]

    def test_remove(self, tmp_path):
        w = Watchlist(tmp_path / "watch.json")
        w.add("AAPL", "MSFT")
        w.remove("AAPL")
        assert w.symbols == ["MSFT"]

    def test_clear(self, tmp_path):
        w = Watchlist(tmp_path / "watch.json")
        w.add("AAPL")
        w.clear()
        assert w.is_empty

    def test_persistence(self, tmp_path):
        path = tmp_path / "watch.json"
        w = Watchlist(path)
        w.add("TSLA")
        w2 = Watchlist(path)
        assert "TSLA" in w2.symbols

    def test_snapshot_empty(self, tmp_path):
        w = Watchlist(tmp_path / "watch.json")
        assert w.snapshot() == []


# ── Dividends ─────────────────────────────────────────────────────────────────

class TestDividends:
    def test_non_payer(self):
        from finscope.dividends import analyze_dividends
        mock_stock = MagicMock()
        mock_stock.info = {"shortName": "Test Corp", "currentPrice": 100}
        with patch("yfinance.Ticker") as mock_yf:
            import pandas as pd
            mock_yf.return_value.dividends = pd.Series(dtype=float)
            result = analyze_dividends("TEST", stock=mock_stock)
        assert result.rating == "Non-Payer"

    def test_with_dividends(self):
        import pandas as pd
        from finscope.dividends import analyze_dividends
        mock_stock = MagicMock()
        mock_stock.info = {
            "shortName": "Stable Inc", "currentPrice": 100,
            "dividendRate": 2.0, "dividendYield": 0.02, "payoutRatio": 0.40,
        }
        dates = pd.date_range("2020-01-01", periods=16, freq="QS")
        divs = pd.Series([0.50] * 16, index=dates)
        with patch("yfinance.Ticker") as mock_yf:
            mock_yf.return_value.dividends = divs
            result = analyze_dividends("STABLE", stock=mock_stock)
        assert result.years_of_data >= 3
        assert result.rating != "Non-Payer"


# ── Earnings ──────────────────────────────────────────────────────────────────

class TestEarnings:
    def test_basic_analysis(self):
        from finscope.earnings import analyze_earnings
        mock_stock = MagicMock()
        mock_stock.info = {
            "shortName": "Test", "currentPrice": 200,
            "earningsGrowth": 0.15, "revenueGrowth": 0.12,
        }
        with patch("yfinance.Ticker") as mock_yf:
            mock_yf.return_value.calendar = None
            mock_yf.return_value.earnings_history = None
            result = analyze_earnings("TEST", stock=mock_stock)
        assert result.eps_trend == "Growing"
        assert result.revenue_trend == "Growing"

    def test_declining_earnings(self):
        from finscope.earnings import analyze_earnings
        mock_stock = MagicMock()
        mock_stock.info = {
            "shortName": "Weak", "currentPrice": 50,
            "earningsGrowth": -0.20, "revenueGrowth": -0.10,
        }
        with patch("yfinance.Ticker") as mock_yf:
            mock_yf.return_value.calendar = None
            mock_yf.return_value.earnings_history = None
            result = analyze_earnings("WEAK", stock=mock_stock)
        assert result.eps_trend == "Declining"
        assert result.rating == "Weak"


# ── Peers ─────────────────────────────────────────────────────────────────────

class TestPeers:
    def test_empty_universe(self):
        from finscope.peers import discover_peers
        mock_stock = MagicMock()
        mock_stock.info = {"sector": "Technology", "industry": "Software", "shortName": "Test"}
        with patch("finscope.screener.engine.get_sp500_tickers", return_value=[]):
            result = discover_peers("TEST", stock=mock_stock)
        assert result.peer_count == 0

    def test_target_metrics_set(self):
        from finscope.peers import discover_peers
        mock_stock = MagicMock()
        mock_stock.info = {"sector": "Tech", "industry": "SW", "shortName": "Test",
                           "trailingPE": 25.0, "marketCap": 100e9}
        with patch("finscope.screener.engine.get_sp500_tickers", return_value=[]):
            with patch("finscope.peers.engine._fetch_peer_info") as mock_fetch:
                from finscope.peers.engine import PeerMetric
                mock_fetch.return_value = PeerMetric(symbol="TEST", pe=25.0)
                result = discover_peers("TEST", stock=mock_stock)
        assert result.target_symbol == "TEST"


# ── CLI dispatch ──────────────────────────────────────────────────────────────

class TestCLIDispatch:
    def test_dividends_dispatch(self):
        from finscope.cli import _build_parser, _dispatch
        ns = _build_parser().parse_args(["AAPL", "dividends"])
        with patch("finscope.cli.cmd_dividends") as mock:
            _dispatch(ns)
        mock.assert_called_once_with("AAPL")

    def test_earnings_dispatch(self):
        from finscope.cli import _build_parser, _dispatch
        ns = _build_parser().parse_args(["AAPL", "earnings"])
        with patch("finscope.cli.cmd_earnings") as mock:
            _dispatch(ns)
        mock.assert_called_once_with("AAPL")

    def test_peers_dispatch(self):
        from finscope.cli import _build_parser, _dispatch
        ns = _build_parser().parse_args(["AAPL", "peers"])
        with patch("finscope.cli.cmd_peers") as mock:
            _dispatch(ns)
        mock.assert_called_once_with("AAPL")

    def test_portfolio_dispatch(self):
        from finscope.cli import _build_parser, _dispatch
        ns = _build_parser().parse_args(["portfolio"])
        with patch("finscope.cli.cmd_portfolio") as mock:
            _dispatch(ns)
        mock.assert_called_once()

    def test_watch_dispatch(self):
        from finscope.cli import _build_parser, _dispatch
        ns = _build_parser().parse_args(["watch"])
        with patch("finscope.cli.cmd_watch") as mock:
            _dispatch(ns)
        mock.assert_called_once()
