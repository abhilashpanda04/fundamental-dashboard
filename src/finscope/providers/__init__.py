"""Data providers package.

Each provider encapsulates communication with one external data source.
Providers implement the abstract ``StockDataProvider`` interface so that
the service layer can swap them transparently (Strategy Pattern).
"""

from finscope.providers.base import StockDataProvider, MutualFundProvider
from finscope.providers.yahoo_provider import YahooFinanceProvider
from finscope.providers.sec_edgar_provider import SecEdgarProvider
from finscope.providers.mfapi_provider import MfapiProvider

__all__ = [
    "StockDataProvider",
    "MutualFundProvider",
    "YahooFinanceProvider",
    "SecEdgarProvider",
    "MfapiProvider",
]
