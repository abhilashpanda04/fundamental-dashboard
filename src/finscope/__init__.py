"""finscope — terminal-based financial research library.

finscope lets you scope deeply into any stock, ETF, or mutual fund from
Python code or the terminal.  All data is fetched lazily and cached so
you only pay for what you access.

Quick start
-----------
::

    import finscope

    # ── Single stock ──────────────────────────────────────────────────────────
    aapl = finscope.stock("AAPL")

    aapl.ratios.pe_ratio           # 28.5
    aapl.ratios.market_cap         # 2_700_000_000_000
    aapl.price_history("1y")       # pandas DataFrame (OHLCV)
    aapl.sparkline                 # [100.0, 105.3, …]  — 3-month trend
    aapl.news                      # list of article dicts
    aapl.financials                # annual income statement
    aapl.balance_sheet
    aapl.cashflow
    aapl.analyst_recommendations
    aapl.holders
    aapl.sec_financials            # XBRL data direct from SEC EDGAR
    aapl.sec_filings(count=10)
    aapl.insider_transactions
    aapl.export_html("aapl_report.html")

    # ── Multi-stock comparison ────────────────────────────────────────────────
    aapl.compare_with("MSFT", "GOOGL")   # list[ComparisonData]
    finscope.compare("AAPL", "MSFT", "GOOGL")  # same, standalone

    # ── Global ETF / mutual fund ──────────────────────────────────────────────
    vwrl = finscope.fund("VWRL.L")
    vwrl.info
    vwrl.returns
    vwrl.sparkline

    # ── Advanced: use services directly ──────────────────────────────────────
    from finscope import StockAnalysisService
    svc = StockAnalysisService()
    svc.get_info("TSLA")

Data sources (all free, no API key required)
--------------------------------------------
- Yahoo Finance  — prices, ratios, financials, news, ETFs
- SEC EDGAR      — XBRL 10-K/10-Q financials, filings, insider trades
- MFAPI.in       — 37,500+ Indian mutual fund NAV histories
"""

from __future__ import annotations

__version__ = "1.0.0"
__author__ = "Abhilash Panda"
__license__ = "MIT"

# ── Core classes ──────────────────────────────────────────────────────────────
from finscope.stock import Fund, Stock

# ── Domain models ─────────────────────────────────────────────────────────────
from finscope.models import (
    ComparisonData,
    FundReturn,
    IndiaFundMeta,
    KeyRatios,
    NavRecord,
    PriceBar,
    SecFiling,
    StockQuote,
)

# ── Exceptions ────────────────────────────────────────────────────────────────
from finscope.exceptions import (
    CIKNotFoundError,
    DataFetchError,
    FinScopeError,
    FundNotFoundError,
    InvalidPeriodError,
    TickerNotFoundError,
)

# ── Services (for advanced / programmatic use) ────────────────────────────────
from finscope.services import FundAnalysisService, StockAnalysisService

# ── Providers (for dependency injection / testing) ────────────────────────────
from finscope.providers import MfapiProvider, SecEdgarProvider, YahooFinanceProvider


# ── Top-level factory functions ───────────────────────────────────────────────

def stock(symbol: str) -> Stock:
    """Create a lazily-loaded :class:`Stock` for *symbol*.

    Args:
        symbol: Ticker symbol, case-insensitive (e.g. ``"AAPL"``, ``"TSLA"``).

    Returns:
        A :class:`Stock` instance.  No network call is made until you access
        a data property.

    Example::

        aapl = finscope.stock("AAPL")
        print(aapl.ratios.pe_ratio)
    """
    return Stock(symbol)


def fund(symbol: str) -> Fund:
    """Create a lazily-loaded :class:`Fund` for *symbol*.

    Args:
        symbol: Yahoo Finance ticker for an ETF or mutual fund
                (e.g. ``"VWRL.L"``, ``"INDA"``, ``"AGG"``).

    Returns:
        A :class:`Fund` instance.

    Example::

        vwrl = finscope.fund("VWRL.L")
        print(vwrl.returns)
    """
    return Fund(symbol)


def compare(*symbols: str) -> list[ComparisonData]:
    """Compare multiple tickers side-by-side.

    Args:
        *symbols: Two or more ticker symbols.

    Returns:
        A list of :class:`ComparisonData` objects, one per symbol.

    Example::

        results = finscope.compare("AAPL", "MSFT", "GOOGL")
        for r in results:
            print(r.symbol, r.pe_ratio)
    """
    svc = StockAnalysisService()
    return svc.get_comparison_data(list(symbols))


# ── Public API surface ────────────────────────────────────────────────────────

__all__ = [
    # Version
    "__version__",
    # Factory functions
    "stock",
    "fund",
    "compare",
    # Core classes
    "Stock",
    "Fund",
    # Domain models
    "KeyRatios",
    "ComparisonData",
    "StockQuote",
    "PriceBar",
    "SecFiling",
    "IndiaFundMeta",
    "NavRecord",
    "FundReturn",
    # Exceptions
    "FinScopeError",
    "TickerNotFoundError",
    "DataFetchError",
    "CIKNotFoundError",
    "FundNotFoundError",
    "InvalidPeriodError",
    # Services
    "StockAnalysisService",
    "FundAnalysisService",
    # Providers
    "YahooFinanceProvider",
    "SecEdgarProvider",
    "MfapiProvider",
]
