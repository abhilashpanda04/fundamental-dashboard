"""Mutual fund analysis service — Facade Pattern.

``FundAnalysisService`` hides all provider complexity behind a clean,
high-level API consumed exclusively by the CLI layer.
"""

from __future__ import annotations

import logging

from finscope.exceptions import FundNotFoundError
from finscope.providers.mfapi_provider import MfapiProvider

logger = logging.getLogger(__name__)


class FundAnalysisService:
    """Orchestrates the MFAPI + Yahoo Finance fund provider (Facade Pattern)."""

    def __init__(self, provider: MfapiProvider | None = None) -> None:
        self._provider = provider or MfapiProvider()

    # ── Indian funds ──────────────────────────────────────────────────────────

    def search_india_funds(self, query: str) -> list[dict]:
        """Search Indian mutual funds by name."""
        return self._provider.search_funds(query)

    def get_india_fund_detail(self, scheme_code: str) -> dict | None:
        """Return full NAV history + metadata for an Indian fund."""
        try:
            return self._provider.get_fund_detail(scheme_code)
        except FundNotFoundError as exc:
            logger.warning("India fund not found: %s", exc)
            return None

    def calculate_india_fund_returns(self, nav_data: list[dict]) -> dict:
        """Calculate point-to-point returns from raw MFAPI NAV data."""
        return self._provider._calculate_returns(nav_data)

    def get_india_fund_nav_series(self, nav_data: list[dict], days: int = 365) -> list[float]:
        """Return NAV values for the last *days* days as a list."""
        return self._provider._nav_series(nav_data, days=days)

    # ── Global funds / ETFs ───────────────────────────────────────────────────

    def get_global_fund_info(self, symbol: str) -> dict | None:
        """Return Yahoo Finance info for a global ETF / mutual fund."""
        return self._provider.get_global_fund_info(symbol)

    def get_global_fund_returns(self, symbol: str) -> dict:
        """Return calculated returns for a global fund."""
        return self._provider.get_global_fund_returns(symbol)

    def get_global_fund_sparkline(self, symbol: str, period: str = "1y") -> list[float]:
        """Return closing prices for sparkline rendering."""
        return self._provider.get_global_fund_sparkline(symbol, period)

    def get_popular_funds_snapshot(self, region: str) -> list[dict]:
        """Return a quick snapshot of popular funds for a region."""
        return self._provider.get_popular_funds_snapshot(region)

    # ── Constants re-exported for the CLI ─────────────────────────────────────

    @property
    def popular_fund_regions(self) -> list[str]:
        """Return all available region keys."""
        from finscope.providers.mfapi_provider import POPULAR_FUNDS
        return list(POPULAR_FUNDS.keys())
