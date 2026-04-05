"""Backward-compatible data access layer.

All functions delegate to the new ``YahooFinanceProvider``.  Existing code
that imports from ``dashboard.data`` continues to work without modification.

.. deprecated::
    Prefer importing from ``dashboard.providers.yahoo_provider`` directly.
"""

from __future__ import annotations

import yfinance as yf
import pandas as pd

from dashboard.providers.yahoo_provider import YahooFinanceProvider

_provider = YahooFinanceProvider()


def get_ticker(symbol: str) -> yf.Ticker:
    """Create a yfinance Ticker object."""
    return yf.Ticker(symbol)


def get_company_info(ticker: yf.Ticker) -> dict:
    return ticker.info


def get_financials(ticker: yf.Ticker) -> pd.DataFrame:
    return ticker.financials


def get_balance_sheet(ticker: yf.Ticker) -> pd.DataFrame:
    return ticker.balance_sheet


def get_cashflow(ticker: yf.Ticker) -> pd.DataFrame:
    return ticker.cashflow


def get_price_history(ticker: yf.Ticker, period: str = "1mo") -> pd.DataFrame:
    return ticker.history(period=period)


def get_news(ticker: yf.Ticker) -> list[dict]:
    return ticker.news or []


def get_analyst_recommendations(ticker: yf.Ticker) -> pd.DataFrame | None:
    try:
        recs = ticker.recommendations
        if recs is not None and not recs.empty:
            return recs
    except Exception:
        pass
    return None


def get_major_holders(
    ticker: yf.Ticker,
) -> tuple[pd.DataFrame | None, pd.DataFrame | None]:
    breakdown = None
    institutional = None
    try:
        breakdown = ticker.major_holders
    except Exception:
        pass
    try:
        institutional = ticker.institutional_holders
    except Exception:
        pass
    return breakdown, institutional


def get_sparkline_data(ticker: yf.Ticker, period: str = "3mo") -> list[float]:
    df = ticker.history(period=period)
    if df.empty:
        return []
    close = df["Close"]
    if hasattr(close, "columns"):
        close = close.iloc[:, 0]
    return close.dropna().tolist()


def get_key_ratios(info: dict) -> dict:
    from dashboard.models import KeyRatios
    return KeyRatios.from_info(info).to_display_dict()


def get_comparison_data(symbols: list[str]) -> list[dict]:
    return _provider.get_comparison_data(symbols)
