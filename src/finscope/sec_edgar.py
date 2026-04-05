"""Backward-compatible SEC EDGAR module.

All functions delegate to the new ``SecEdgarProvider``.

.. deprecated::
    Prefer importing from ``finscope.providers.sec_edgar_provider`` directly.
"""

from __future__ import annotations

from functools import lru_cache

from finscope.exceptions import CIKNotFoundError, DataFetchError
from finscope.providers.sec_edgar_provider import SecEdgarProvider

_provider = SecEdgarProvider()


def get_cik(symbol: str) -> str | None:
    try:
        return _provider.get_cik(symbol)
    except CIKNotFoundError:
        return None


def get_company_facts(symbol: str) -> dict | None:
    try:
        return _provider.get_company_facts(symbol)
    except (CIKNotFoundError, DataFetchError):
        return None


def extract_gaap_concept(facts: dict, concept: str, form: str = "10-K") -> list[dict]:
    return _provider.extract_gaap_concept(facts, concept, form)


def get_detailed_financials(symbol: str) -> dict:
    return _provider.get_detailed_financials(symbol)


def get_recent_filings(symbol: str, count: int = 20) -> list[dict]:
    try:
        return _provider.get_recent_filings(symbol, count=count)
    except (CIKNotFoundError, DataFetchError):
        return []


def get_insider_transactions(symbol: str) -> list[dict]:
    return _provider.get_insider_transactions(symbol)
