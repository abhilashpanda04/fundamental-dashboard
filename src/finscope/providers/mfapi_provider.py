"""MFAPI & Yahoo Finance mutual fund provider — concrete Strategy implementation.

- Indian funds: MFAPI.in (37 500+ SEBI-registered schemes, completely free)
- Global ETFs / US funds: Yahoo Finance via ``yfinance``
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from functools import lru_cache

import pandas as pd
import requests
import yfinance as yf

__all__ = ["MfapiProvider", "POPULAR_FUNDS"]

from finscope.config import config
from finscope.exceptions import DataFetchError, FundNotFoundError
from finscope.providers.base import MutualFundProvider

logger = logging.getLogger(__name__)

_MFAPI_BASE = "https://api.mfapi.in/mf"

# ── Curated popular fund lists ─────────────────────────────────────────────────
POPULAR_FUNDS: dict[str, list[tuple[str, str]]] = {
    "US": [
        ("VFIAX", "Vanguard 500 Index (Admiral)"),
        ("FXAIX", "Fidelity 500 Index"),
        ("VTSAX", "Vanguard Total Stock Market (Admiral)"),
        ("FCNTX", "Fidelity Contrafund"),
        ("AGTHX", "American Funds Growth Fund"),
        ("DODGX", "Dodge & Cox Stock"),
        ("PTTRX", "PIMCO Total Return"),
        ("VBTLX", "Vanguard Total Bond Market"),
    ],
    "Global ETF (LSE)": [
        ("VWRL.L", "Vanguard FTSE All-World"),
        ("SWDA.L", "iShares Core MSCI World"),
        ("EIMI.L", "iShares Core MSCI EM IMI"),
        ("CSPX.L", "iShares Core S&P 500"),
        ("VUSA.L", "Vanguard S&P 500 (GBP)"),
        ("AGGG.L", "iShares Core Global Agg Bond"),
        ("VFEM.L", "Vanguard FTSE Emerging Markets"),
        ("ISF.L", "iShares Core FTSE 100"),
    ],
    "Asia Pacific ETF": [
        ("EWJ", "iShares MSCI Japan"),
        ("EWY", "iShares MSCI South Korea"),
        ("EWT", "iShares MSCI Taiwan"),
        ("EWA", "iShares MSCI Australia"),
        ("FXI", "iShares China Large-Cap"),
        ("MCHI", "iShares MSCI China"),
        ("INDA", "iShares MSCI India"),
        ("VPL", "Vanguard FTSE Pacific"),
    ],
    "European ETF": [
        ("EZU", "iShares MSCI Eurozone"),
        ("EWG", "iShares MSCI Germany"),
        ("EWQ", "iShares MSCI France"),
        ("EWI", "iShares MSCI Italy"),
        ("EWP", "iShares MSCI Spain"),
        ("EWN", "iShares MSCI Netherlands"),
        ("EWL", "iShares MSCI Switzerland"),
    ],
    "Fixed Income / Bond ETF": [
        ("AGG", "iShares Core US Aggregate Bond"),
        ("BND", "Vanguard Total Bond Market"),
        ("TLT", "iShares 20+ Year Treasury"),
        ("HYG", "iShares iBoxx USD High Yield"),
        ("EMB", "iShares JP Morgan USD EM Bond"),
        ("BNDX", "Vanguard Total International Bond"),
    ],
}


class MfapiProvider(MutualFundProvider):
    """Fetches Indian fund data from MFAPI.in and global fund data from Yahoo Finance."""

    # ── Indian funds (MFAPI) ─────────────────────────────────────────────────

    @lru_cache(maxsize=1)  # noqa: B019
    def _all_india_funds(self) -> list[dict]:
        """Fetch and cache the complete MFAPI fund list (~37 500 entries)."""
        try:
            r = requests.get(_MFAPI_BASE, timeout=config.request_timeout)
            r.raise_for_status()
            return r.json()
        except Exception as exc:
            raise DataFetchError("MFAPI", f"Failed to fetch fund list: {exc}") from exc

    def search_funds(self, query: str) -> list[dict]:
        """Search Indian mutual funds by name using the MFAPI search endpoint."""
        try:
            r = requests.get(
                f"{_MFAPI_BASE}/search",
                params={"q": query},
                timeout=config.request_timeout,
            )
            r.raise_for_status()
            return r.json()
        except Exception:
            # Graceful fallback: local text search over the cached full list
            try:
                funds = self._all_india_funds()
                q = query.lower()
                return [f for f in funds if q in f["schemeName"].lower()][:20]
            except DataFetchError:
                return []

    def get_fund_detail(self, identifier: str) -> dict | None:
        """Return full NAV history + metadata for an Indian fund scheme code."""
        try:
            r = requests.get(
                f"{_MFAPI_BASE}/{identifier}",
                timeout=config.request_timeout,
            )
            r.raise_for_status()
            return r.json()
        except Exception as exc:
            raise FundNotFoundError(identifier) from exc

    def get_fund_returns(self, identifier: str) -> dict:
        """Calculate point-to-point returns from MFAPI NAV history."""
        detail = self.get_fund_detail(identifier)
        if not detail:
            return {}
        nav_data = detail.get("data", [])
        return self._calculate_returns(nav_data)

    def get_fund_sparkline(self, identifier: str, period: str = "1y") -> list[float]:
        """Return NAV series for the last *period* as a float list."""
        try:
            detail = self.get_fund_detail(identifier)
        except FundNotFoundError:
            return []
        if not detail:
            return []

        days_map = {"1y": 365, "3mo": 90, "6mo": 180, "2y": 730}
        days = days_map.get(period, 365)
        nav_data = detail.get("data", [])
        return self._nav_series(nav_data, days=days)

    # ── Global / Yahoo Finance ────────────────────────────────────────────────

    def get_global_fund_info(self, symbol: str) -> dict | None:
        """Return Yahoo Finance info dict for an ETF / mutual fund."""
        try:
            info = yf.Ticker(symbol).info
            if not info or info.get("quoteType") is None:
                return None
            return info
        except Exception as exc:
            logger.warning("Failed to fetch global fund %s: %s", symbol, exc)
            return None

    def get_global_fund_returns(self, symbol: str) -> dict:
        """Calculate historical returns from Yahoo Finance price history."""
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info

            returns: dict = {
                "1Y (Reported)": info.get("ytdReturn"),
                "3Y (Reported)": info.get("threeYearAverageReturn"),
                "5Y (Reported)": info.get("fiveYearAverageReturn"),
            }

            hist = ticker.history(period="5y")
            if not hist.empty:
                close = hist["Close"].dropna()
                if hasattr(close, "columns"):
                    close = close.iloc[:, 0]
                current = float(close.iloc[-1])

                def _pct(days: int) -> float | None:
                    cutoff = close.index[-1] - pd.Timedelta(days=days)
                    past = close[close.index <= cutoff]
                    if not past.empty:
                        return ((current - float(past.iloc[-1])) / float(past.iloc[-1])) * 100
                    return None

                returns.update(
                    {
                        "1W": _pct(7),
                        "1M": _pct(30),
                        "3M": _pct(90),
                        "6M": _pct(180),
                        "1Y": _pct(365),
                        "3Y": _pct(365 * 3),
                        "5Y": _pct(365 * 5),
                    }
                )

            return returns
        except Exception as exc:
            logger.warning("Global fund returns for %s: %s", symbol, exc)
            return {}

    def get_global_fund_sparkline(self, symbol: str, period: str = "1y") -> list[float]:
        """Return closing prices for sparkline rendering."""
        try:
            hist = self.get_price_history(symbol, period=period)
            if hist.empty:
                return []
            close = hist["Close"].dropna()
            if hasattr(close, "columns"):
                close = close.iloc[:, 0]
            return [float(v) for v in close.tolist()]
        except Exception:
            return []

    def get_price_history(self, symbol: str, period: str = "1mo") -> pd.DataFrame:
        """Return full OHLCV price history for a global fund / ETF."""
        try:
            return yf.Ticker(symbol).history(period=period)
        except Exception as exc:
            logger.warning("Global fund price history for %s: %s", symbol, exc)
            return pd.DataFrame()

    def get_popular_funds_snapshot(self, region: str) -> list[dict]:
        """Return a quick overview of popular funds for *region*."""
        fund_list = POPULAR_FUNDS.get(region, [])
        results: list[dict] = []

        for symbol, description in fund_list:
            try:
                info = yf.Ticker(symbol).info
                nav = (
                    info.get("navPrice")
                    or info.get("currentPrice")
                    or info.get("previousClose")
                )
                results.append(
                    {
                        "symbol": symbol,
                        "description": description,
                        "name": info.get("longName") or info.get("shortName") or description,
                        "nav": nav,
                        "change_pct": info.get("regularMarketChangePercent"),
                        "currency": info.get("currency", "USD"),
                        "total_assets": info.get("totalAssets"),
                        "expense_ratio": info.get("annualReportExpenseRatio"),
                        "ytd_return": info.get("ytdReturn"),
                        "sparkline": self.get_global_fund_sparkline(symbol, "1y"),
                    }
                )
            except Exception as exc:
                logger.warning("Skipping %s in snapshot: %s", symbol, exc)

        return results

    # ── Static helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _parse_date(date_str: str) -> datetime:
        return datetime.strptime(date_str, "%d-%m-%Y")

    @classmethod
    def _calculate_returns(cls, nav_data: list[dict]) -> dict:
        """Compute point-to-point returns for standard periods."""
        if not nav_data:
            return {}

        current_nav = float(nav_data[0]["nav"])
        current_date = cls._parse_date(nav_data[0]["date"])

        def find_closest(target: datetime) -> tuple[float | None, datetime | None]:
            for entry in nav_data:
                d = cls._parse_date(entry["date"])
                if d <= target:
                    return float(entry["nav"]), d
            return None, None

        periods = {
            "1W": 7,
            "1M": 30,
            "3M": 90,
            "6M": 180,
            "1Y": 365,
            "2Y": 365 * 2,
            "3Y": 365 * 3,
            "5Y": 365 * 5,
            "10Y": 365 * 10,
        }

        results: dict = {}
        for label, days in periods.items():
            past_nav, past_date = find_closest(current_date - timedelta(days=days))
            if past_nav and past_date:
                pct = ((current_nav - past_nav) / past_nav) * 100
                results[label] = {
                    "return_pct": pct,
                    "start_nav": past_nav,
                    "start_date": past_date.strftime("%d-%m-%Y"),
                    "current_nav": current_nav,
                }

        return results

    @classmethod
    def _nav_series(cls, nav_data: list[dict], days: int = 365) -> list[float]:
        """Extract NAV float values from the last *days* days (oldest → newest)."""
        if not nav_data:
            return []
        cutoff = datetime.now() - timedelta(days=days)
        values: list[float] = []
        for entry in reversed(nav_data):
            try:
                d = cls._parse_date(entry["date"])
                if d >= cutoff:
                    values.append(float(entry["nav"]))
            except (ValueError, KeyError):
                continue
        return values
