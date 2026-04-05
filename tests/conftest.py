"""Shared pytest fixtures for all test levels.

Fixtures are grouped by scope:
- ``session`` – created once for the entire test run (expensive objects)
- ``function`` – created fresh for every test (most fixtures)

All external HTTP calls are mocked at the unit / smoke level using
``pytest-mock``.  Integration tests are marked ``@pytest.mark.integration``
and deliberately make real network requests.
"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest


# ── Raw yfinance info dict fixture ─────────────────────────────────────────────

@pytest.fixture
def apple_info() -> dict:
    """Minimal yfinance-style info dict for Apple Inc."""
    return {
        "symbol": "AAPL",
        "longName": "Apple Inc.",
        "shortName": "Apple Inc.",
        "quoteType": "EQUITY",
        "currentPrice": 175.50,
        "regularMarketPrice": 175.50,
        "regularMarketChangePercent": 1.25,
        "currency": "USD",
        "exchange": "NMS",
        "sector": "Technology",
        "industry": "Consumer Electronics",
        "longBusinessSummary": "Apple Inc. designs, manufactures, and markets smartphones.",
        # Ratios
        "trailingPE": 28.5,
        "forwardPE": 25.0,
        "pegRatio": 2.1,
        "priceToBook": 45.2,
        "priceToSalesTrailing12Months": 7.3,
        "enterpriseToEbitda": 22.1,
        "profitMargins": 0.245,
        "operatingMargins": 0.298,
        "returnOnEquity": 1.47,
        "returnOnAssets": 0.197,
        "debtToEquity": 180.0,
        "currentRatio": 0.98,
        "totalRevenue": 394_328_000_000,
        "ebitda": 125_820_000_000,
        "freeCashflow": 111_442_000_000,
        "marketCap": 2_700_000_000_000,
        "enterpriseValue": 2_750_000_000_000,
        "dividendYield": 0.0056,
        "beta": 1.29,
        "fiftyTwoWeekHigh": 198.23,
        "fiftyTwoWeekLow": 124.17,
        "fiftyDayAverage": 170.12,
        "twoHundredDayAverage": 163.45,
    }


@pytest.fixture
def empty_info() -> dict:
    """Info dict that simulates a ticker-not-found response from yfinance."""
    return {}


@pytest.fixture
def sample_price_df() -> pd.DataFrame:
    """Small OHLCV DataFrame for price history tests."""
    dates = pd.date_range("2024-01-01", periods=5, freq="B")
    return pd.DataFrame(
        {
            "Open":   [150.0, 152.0, 149.0, 153.0, 155.0],
            "High":   [155.0, 156.0, 154.0, 157.0, 158.0],
            "Low":    [149.0, 150.0, 147.0, 151.0, 153.0],
            "Close":  [153.0, 151.0, 153.0, 156.0, 157.0],
            "Volume": [80_000_000, 70_000_000, 90_000_000, 65_000_000, 75_000_000],
        },
        index=dates,
    )


@pytest.fixture
def sample_financials_df() -> pd.DataFrame:
    """Minimal income statement DataFrame."""
    cols = pd.to_datetime(["2023-09-30", "2022-09-30", "2021-09-30"])
    return pd.DataFrame(
        {
            cols[0]: [394_328e6, 274_515e6, 10_044e6],
            cols[1]: [365_817e6, 258_956e6,  9_680e6],
            cols[2]: [274_515e6, 191_573e6,  8_101e6],
        },
        index=["Total Revenue", "Gross Profit", "Net Income"],
    )


@pytest.fixture
def sample_news() -> list[dict]:
    """A pair of news article dicts."""
    return [
        {
            "title": "Apple reports record Q4 earnings",
            "publisher": "Reuters",
            "link": "https://reuters.com/article/1",
        },
        {
            "title": "Apple launches new iPhone model",
            "publisher": "Bloomberg",
            "link": "https://bloomberg.com/article/2",
        },
    ]


@pytest.fixture
def sample_analyst_recs() -> pd.DataFrame:
    """Single-row analyst recommendations DataFrame."""
    return pd.DataFrame(
        {
            "strongBuy": [15],
            "buy": [20],
            "hold": [10],
            "sell": [3],
            "strongSell": [1],
        }
    )


@pytest.fixture
def sample_sparkline() -> list[float]:
    """Simple price series for sparkline tests."""
    return [100.0, 102.0, 101.0, 105.0, 108.0, 107.0, 110.0]


@pytest.fixture
def sample_nav_data() -> list[dict]:
    """Raw MFAPI-style NAV records (newest first)."""
    return [
        {"date": "04-01-2024", "nav": "105.2341"},
        {"date": "03-01-2024", "nav": "104.8921"},
        {"date": "02-01-2024", "nav": "104.1234"},
        {"date": "01-01-2024", "nav": "103.5678"},
        {"date": "04-01-2023", "nav":  "90.1234"},  # ~1 year ago
        {"date": "04-01-2022", "nav":  "75.0000"},  # ~2 years ago
    ]


@pytest.fixture
def sample_sec_filing() -> dict:
    return {
        "form": "10-K",
        "date": "2023-11-03",
        "accession": "0000320193-23-000106",
        "document": "aapl-20230930.htm",
        "description": "Annual Report",
        "url": "https://www.sec.gov/Archives/edgar/data/320193/000032019323000106/aapl-20230930.htm",
    }


@pytest.fixture
def sample_comparison_data() -> list[dict]:
    """List of comparison dicts as returned by ``YahooFinanceProvider.get_comparison_data``."""
    return [
        {
            "symbol": "AAPL",
            "name": "Apple Inc.",
            "price": 175.5,
            "change_pct": 1.25,
            "market_cap": 2_700_000_000_000,
            "pe_ratio": 28.5,
            "forward_pe": 25.0,
            "peg": 2.1,
            "pb": 45.2,
            "ps": 7.3,
            "profit_margin": 0.245,
            "roe": 1.47,
            "debt_equity": 180.0,
            "dividend_yield": 0.0056,
            "beta": 1.29,
            "revenue": 394_328_000_000,
            "ebitda": 125_820_000_000,
            "sparkline": [100.0, 105.0, 110.0],
        },
        {
            "symbol": "MSFT",
            "name": "Microsoft Corporation",
            "price": 330.0,
            "change_pct": -0.5,
            "market_cap": 2_450_000_000_000,
            "pe_ratio": 35.0,
            "forward_pe": 30.0,
            "peg": 2.5,
            "pb": 12.0,
            "ps": 11.0,
            "profit_margin": 0.34,
            "roe": 0.42,
            "debt_equity": 45.0,
            "dividend_yield": 0.009,
            "beta": 0.92,
            "revenue": 211_915_000_000,
            "ebitda": 98_000_000_000,
            "sparkline": [200.0, 210.0, 205.0],
        },
    ]


# ── Mock yfinance Ticker ──────────────────────────────────────────────────────

@pytest.fixture
def mock_yf_ticker(apple_info, sample_price_df, sample_financials_df, sample_news):
    """A fully configured MagicMock mimicking a yfinance.Ticker object."""
    ticker = MagicMock()
    ticker.info = apple_info
    ticker.history.return_value = sample_price_df
    ticker.financials = sample_financials_df
    ticker.balance_sheet = sample_financials_df.copy()
    ticker.cashflow = sample_financials_df.copy()
    ticker.news = sample_news
    ticker.recommendations = pd.DataFrame(
        {"strongBuy": [15], "buy": [20], "hold": [10], "sell": [3], "strongSell": [1]}
    )
    ticker.major_holders = None
    ticker.institutional_holders = None
    return ticker
