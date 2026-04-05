"""Abstract provider interfaces — Strategy Pattern.

Defining behaviour through abstract base classes (ABCs) means the service
layer depends on the *abstraction*, not any concrete implementation.  Any
provider that satisfies the ABC can be swapped in without touching callers.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd

__all__ = ["StockDataProvider", "MutualFundProvider"]


class StockDataProvider(ABC):
    """Abstract strategy for fetching equity / stock market data."""

    # ── Core data ────────────────────────────────────────────────────────────

    @abstractmethod
    def get_info(self, symbol: str) -> dict:
        """Return a metadata dict for *symbol*.

        Raises:
            TickerNotFoundError: When the symbol is not recognised.
            DataFetchError: On network / API failures.
        """

    @abstractmethod
    def get_price_history(self, symbol: str, period: str = "1mo") -> pd.DataFrame:
        """Return an OHLCV DataFrame for *symbol* over *period*.

        Args:
            symbol: Ticker symbol (e.g. ``"AAPL"``).
            period: yfinance-compatible period string.

        Raises:
            DataFetchError: On network / API failures.
        """

    @abstractmethod
    def get_financials(self, symbol: str) -> pd.DataFrame:
        """Return the annual income statement as a DataFrame."""

    @abstractmethod
    def get_balance_sheet(self, symbol: str) -> pd.DataFrame:
        """Return the annual balance sheet as a DataFrame."""

    @abstractmethod
    def get_cashflow(self, symbol: str) -> pd.DataFrame:
        """Return the annual cash flow statement as a DataFrame."""

    @abstractmethod
    def get_news(self, symbol: str) -> list[dict]:
        """Return a list of recent news article dicts."""

    @abstractmethod
    def get_analyst_recommendations(self, symbol: str) -> pd.DataFrame | None:
        """Return analyst recommendations DataFrame or ``None``."""

    @abstractmethod
    def get_major_holders(self, symbol: str) -> tuple[pd.DataFrame | None, pd.DataFrame | None]:
        """Return ``(breakdown, institutional_holders)`` DataFrames."""

    @abstractmethod
    def get_sparkline(self, symbol: str, period: str = "3mo") -> list[float]:
        """Return a list of closing prices suitable for sparkline rendering."""

    @abstractmethod
    def get_comparison_data(self, symbols: list[str]) -> list[dict]:
        """Return key metrics for multiple tickers for side-by-side comparison."""


class MutualFundProvider(ABC):
    """Abstract strategy for fetching mutual fund data."""

    @abstractmethod
    def search_funds(self, query: str) -> list[dict]:
        """Search for funds matching *query* by name."""

    @abstractmethod
    def get_fund_detail(self, identifier: str) -> dict | None:
        """Return full fund detail including NAV history."""

    @abstractmethod
    def get_fund_returns(self, identifier: str) -> dict:
        """Return a period-label → return-data mapping."""

    @abstractmethod
    def get_fund_sparkline(self, identifier: str, period: str = "1y") -> list[float]:
        """Return closing NAV values for sparkline rendering."""
