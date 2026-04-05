"""Backward-compatible mutual funds module.

All functions delegate to ``MfapiProvider``.

.. deprecated::
    Prefer importing from ``dashboard.providers.mfapi_provider`` directly.
"""

from __future__ import annotations

from dashboard.providers.mfapi_provider import POPULAR_FUNDS, MfapiProvider

_provider = MfapiProvider()


def search_india_funds(query: str) -> list[dict]:
    return _provider.search_funds(query)


def get_india_fund_detail(scheme_code: str | int) -> dict | None:
    try:
        return _provider.get_fund_detail(str(scheme_code))
    except Exception:
        return None


def calculate_india_fund_returns(nav_data: list[dict]) -> dict:
    return _provider._calculate_returns(nav_data)


def get_india_fund_nav_series(nav_data: list[dict], days: int = 365) -> list[float]:
    return _provider._nav_series(nav_data, days=days)


def get_global_fund_info(symbol: str) -> dict | None:
    return _provider.get_global_fund_info(symbol)


def get_global_fund_returns(symbol: str) -> dict:
    return _provider.get_global_fund_returns(symbol)


def get_global_fund_sparkline(symbol: str, period: str = "1y") -> list[float]:
    return _provider.get_global_fund_sparkline(symbol, period)


def get_popular_funds_snapshot(region: str) -> list[dict]:
    return _provider.get_popular_funds_snapshot(region)
