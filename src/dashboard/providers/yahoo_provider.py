"""Yahoo Finance data provider — concrete Strategy implementation.

Wraps ``yfinance`` and converts library-specific exceptions into the
application's own exception hierarchy so callers never depend on yfinance
directly.
"""

from __future__ import annotations

import logging

import pandas as pd
import yfinance as yf

from dashboard.exceptions import DataFetchError, TickerNotFoundError
from dashboard.providers.base import StockDataProvider

logger = logging.getLogger(__name__)


class YahooFinanceProvider(StockDataProvider):
    """Fetches all equity data from Yahoo Finance via the ``yfinance`` library."""

    # ── Private helpers ───────────────────────────────────────────────────────

    def _ticker(self, symbol: str) -> yf.Ticker:
        """Return a ``yfinance.Ticker`` for *symbol*."""
        return yf.Ticker(symbol)

    @staticmethod
    def _safe_float(val) -> float | None:
        """Coerce a possibly-nested yfinance value to float or ``None``."""
        if val is None:
            return None
        if hasattr(val, "__iter__") and not isinstance(val, str):
            items = list(val)
            return float(items[0]) if items else None
        try:
            return float(val)
        except (TypeError, ValueError):
            return None

    # ── StockDataProvider interface ───────────────────────────────────────────

    def get_info(self, symbol: str) -> dict:
        """Return a metadata dict for *symbol*.

        Raises:
            TickerNotFoundError: When the symbol is not recognised.
            DataFetchError: On network / API failures.
        """
        try:
            info = self._ticker(symbol).info
        except Exception as exc:
            raise DataFetchError("Yahoo Finance", str(exc)) from exc

        if not info or info.get("quoteType") is None:
            raise TickerNotFoundError(symbol)

        return info

    def get_price_history(self, symbol: str, period: str = "1mo") -> pd.DataFrame:
        try:
            return self._ticker(symbol).history(period=period)
        except Exception as exc:
            raise DataFetchError("Yahoo Finance", str(exc)) from exc

    def get_financials(self, symbol: str) -> pd.DataFrame:
        try:
            return self._ticker(symbol).financials
        except Exception as exc:
            raise DataFetchError("Yahoo Finance", str(exc)) from exc

    def get_balance_sheet(self, symbol: str) -> pd.DataFrame:
        try:
            return self._ticker(symbol).balance_sheet
        except Exception as exc:
            raise DataFetchError("Yahoo Finance", str(exc)) from exc

    def get_cashflow(self, symbol: str) -> pd.DataFrame:
        try:
            return self._ticker(symbol).cashflow
        except Exception as exc:
            raise DataFetchError("Yahoo Finance", str(exc)) from exc

    def get_news(self, symbol: str) -> list[dict]:
        try:
            return self._ticker(symbol).news or []
        except Exception as exc:
            logger.warning("Failed to fetch news for %s: %s", symbol, exc)
            return []

    def get_analyst_recommendations(self, symbol: str) -> pd.DataFrame | None:
        try:
            recs = self._ticker(symbol).recommendations
            if recs is not None and not recs.empty:
                return recs
        except Exception as exc:
            logger.warning("Failed to fetch recommendations for %s: %s", symbol, exc)
        return None

    def get_major_holders(
        self, symbol: str
    ) -> tuple[pd.DataFrame | None, pd.DataFrame | None]:
        ticker = self._ticker(symbol)

        breakdown: pd.DataFrame | None = None
        institutional: pd.DataFrame | None = None

        try:
            breakdown = ticker.major_holders
        except Exception as exc:
            logger.warning("Failed to fetch major holders for %s: %s", symbol, exc)

        try:
            institutional = ticker.institutional_holders
        except Exception as exc:
            logger.warning("Failed to fetch institutional holders for %s: %s", symbol, exc)

        return breakdown, institutional

    def get_sparkline(self, symbol: str, period: str = "3mo") -> list[float]:
        try:
            df = self._ticker(symbol).history(period=period)
            if df.empty:
                return []
            close = df["Close"]
            if hasattr(close, "columns"):
                close = close.iloc[:, 0]
            return close.dropna().tolist()
        except Exception as exc:
            logger.warning("Failed to fetch sparkline for %s: %s", symbol, exc)
            return []

    def get_comparison_data(self, symbols: list[str]) -> list[dict]:
        results: list[dict] = []
        for symbol in symbols:
            try:
                info = self.get_info(symbol)
                sparkline = self.get_sparkline(symbol, period="3mo")
                results.append(
                    {
                        "symbol": symbol.upper(),
                        "name": info.get("shortName", "N/A"),
                        "price": info.get("currentPrice") or info.get("regularMarketPrice"),
                        "change_pct": info.get("regularMarketChangePercent"),
                        "market_cap": info.get("marketCap"),
                        "pe_ratio": info.get("trailingPE"),
                        "forward_pe": info.get("forwardPE"),
                        "peg": info.get("pegRatio"),
                        "pb": info.get("priceToBook"),
                        "ps": info.get("priceToSalesTrailing12Months"),
                        "profit_margin": info.get("profitMargins"),
                        "roe": info.get("returnOnEquity"),
                        "debt_equity": info.get("debtToEquity"),
                        "dividend_yield": info.get("dividendYield"),
                        "beta": info.get("beta"),
                        "revenue": info.get("totalRevenue"),
                        "ebitda": info.get("ebitda"),
                        "sparkline": sparkline,
                    }
                )
            except (TickerNotFoundError, DataFetchError) as exc:
                logger.warning("Skipping %s in comparison: %s", symbol, exc)
        return results
