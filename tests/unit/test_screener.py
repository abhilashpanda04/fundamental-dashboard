"""Tests for the stock screener engine."""

from unittest.mock import MagicMock, patch

import pytest

from finscope.screener import screen, get_sp500_tickers
from finscope.screener.engine import _fetch_stock_metrics


def test_get_sp500_tickers_success():
    with patch("pandas.read_html") as mock_read:
        import pandas as pd
        mock_df = pd.DataFrame({"Symbol": ["AAPL", "MSFT", "BRK.B"]})
        mock_read.return_value = [mock_df]
        
        tickers = get_sp500_tickers()
        assert len(tickers) == 3
        assert "AAPL" in tickers
        assert "BRK-B" in tickers  # dot replaced with dash


def test_get_sp500_tickers_failure():
    with patch("pandas.read_html", side_effect=Exception("Network error")):
        tickers = get_sp500_tickers()
        assert tickers == []


def test_fetch_stock_metrics(apple_info):
    mock_stock = MagicMock()
    mock_stock.info = apple_info
    
    mock_ratios = MagicMock()
    mock_ratios.market_cap = 2_000_000_000_000
    mock_ratios.pe_ratio = 28.5
    mock_ratios.forward_pe = 26.0
    mock_ratios.price_to_book = 40.0
    mock_ratios.price_to_sales = 6.0
    mock_ratios.dividend_yield = 0.005  # 0.5%
    mock_ratios.return_on_equity = 1.5
    mock_ratios.return_on_assets = 0.2
    mock_ratios.debt_to_equity = 1.1
    mock_stock.ratios = mock_ratios
    
    with patch("finscope.stock", return_value=mock_stock):
        metrics = _fetch_stock_metrics("AAPL")
        
        assert metrics is not None
        assert metrics["symbol"] == "AAPL"
        assert metrics["pe"] == 28.5
        assert metrics["dividend_yield"] == 0.5
        assert metrics["roe"] == 150.0


def test_screen_with_kwargs():
    universe = ["AAPL", "MSFT"]
    
    def mock_fetch(symbol):
        if symbol == "AAPL":
            return {"symbol": "AAPL", "pe": 28.5, "roe": 150.0}
        return {"symbol": "MSFT", "pe": 35.0, "roe": 40.0}
        
    with patch("finscope.screener.engine._fetch_stock_metrics", side_effect=mock_fetch):
        # PE < 30 should only return AAPL
        results = screen(universe=universe, max_workers=1, pe=("<", 30))
        assert len(results) == 1
        assert results[0].symbol == "AAPL"
        
        # Exact match
        results = screen(universe=universe, max_workers=1, symbol="MSFT")
        assert len(results) == 1
        assert results[0].symbol == "MSFT"


def test_screen_with_query_string():
    universe = ["AAPL", "MSFT", "INTC"]
    
    def mock_fetch(symbol):
        if symbol == "AAPL":
            return {"symbol": "AAPL", "pe": 28.5, "sector": "Technology"}
        if symbol == "MSFT":
            return {"symbol": "MSFT", "pe": 35.0, "sector": "Technology"}
        return {"symbol": "INTC", "pe": 15.0, "sector": "Technology"}
        
    with patch("finscope.screener.engine._fetch_stock_metrics", side_effect=mock_fetch):
        results = screen("pe < 20 and sector == 'Technology'", universe=universe, max_workers=1)
        assert len(results) == 1
        assert results[0].symbol == "INTC"


def test_screen_empty_universe():
    assert screen(universe=[]) == []
