"""Stock analysis service — Facade Pattern.

``StockAnalysisService`` is the single entry-point for all stock-related
operations.  It hides the complexity of coordinating Yahoo Finance and SEC
EDGAR providers behind a clean, intention-revealing API.
"""

from __future__ import annotations

import logging

import pandas as pd

from dashboard.exceptions import DataFetchError, TickerNotFoundError
from dashboard.models import ComparisonData, KeyRatios
from dashboard.providers.sec_edgar_provider import SecEdgarProvider
from dashboard.providers.yahoo_provider import YahooFinanceProvider

logger = logging.getLogger(__name__)


class StockAnalysisService:
    """Orchestrates Yahoo Finance and SEC EDGAR providers (Facade Pattern).

    All public methods are *safe*: they catch provider exceptions, log them,
    and return empty / ``None`` values instead of propagating failures to
    the CLI layer.
    """

    def __init__(
        self,
        yahoo: YahooFinanceProvider | None = None,
        sec: SecEdgarProvider | None = None,
    ) -> None:
        self._yahoo = yahoo or YahooFinanceProvider()
        self._sec = sec or SecEdgarProvider()

    # ── Info / metadata ───────────────────────────────────────────────────────

    def get_info(self, symbol: str) -> dict:
        """Return the raw yfinance info dict.

        Raises:
            TickerNotFoundError: propagated from the provider.
            DataFetchError: propagated from the provider.
        """
        return self._yahoo.get_info(symbol)

    def get_key_ratios(self, info: dict) -> KeyRatios:
        """Build a ``KeyRatios`` object from a raw info dict."""
        return KeyRatios.from_info(info)

    # ── Price data ────────────────────────────────────────────────────────────

    def get_price_history(self, symbol: str, period: str = "1mo") -> pd.DataFrame:
        return self._yahoo.get_price_history(symbol, period)

    def get_sparkline(self, symbol: str, period: str = "3mo") -> list[float]:
        return self._yahoo.get_sparkline(symbol, period)

    # ── Financial statements (Yahoo Finance) ─────────────────────────────────

    def get_financials(self, symbol: str) -> pd.DataFrame:
        return self._yahoo.get_financials(symbol)

    def get_balance_sheet(self, symbol: str) -> pd.DataFrame:
        return self._yahoo.get_balance_sheet(symbol)

    def get_cashflow(self, symbol: str) -> pd.DataFrame:
        return self._yahoo.get_cashflow(symbol)

    # ── Qualitative data ──────────────────────────────────────────────────────

    def get_news(self, symbol: str) -> list[dict]:
        return self._yahoo.get_news(symbol)

    def get_analyst_recommendations(self, symbol: str) -> pd.DataFrame | None:
        return self._yahoo.get_analyst_recommendations(symbol)

    def get_major_holders(
        self, symbol: str
    ) -> tuple[pd.DataFrame | None, pd.DataFrame | None]:
        return self._yahoo.get_major_holders(symbol)

    # ── Multi-ticker ──────────────────────────────────────────────────────────

    def get_comparison_data(self, symbols: list[str]) -> list[ComparisonData]:
        """Return typed ``ComparisonData`` for each symbol."""
        raw = self._yahoo.get_comparison_data(symbols)
        return [
            ComparisonData(
                symbol=item["symbol"],
                name=item.get("name", "N/A"),
                price=item.get("price"),
                change_pct=item.get("change_pct"),
                market_cap=item.get("market_cap"),
                pe_ratio=item.get("pe_ratio"),
                forward_pe=item.get("forward_pe"),
                peg=item.get("peg"),
                pb=item.get("pb"),
                ps=item.get("ps"),
                profit_margin=item.get("profit_margin"),
                roe=item.get("roe"),
                debt_equity=item.get("debt_equity"),
                dividend_yield=item.get("dividend_yield"),
                beta=item.get("beta"),
                revenue=item.get("revenue"),
                ebitda=item.get("ebitda"),
                sparkline=item.get("sparkline", []),
            )
            for item in raw
        ]

    # ── SEC EDGAR ─────────────────────────────────────────────────────────────

    def get_detailed_financials(self, symbol: str) -> dict:
        """Return XBRL financial data, or ``{}`` on any failure."""
        return self._sec.get_detailed_financials(symbol)

    def get_recent_filings(self, symbol: str, count: int = 20) -> list[dict]:
        try:
            return self._sec.get_recent_filings(symbol, count=count)
        except Exception as exc:
            logger.warning("SEC filings for %s: %s", symbol, exc)
            return []

    def get_insider_transactions(self, symbol: str) -> list[dict]:
        return self._sec.get_insider_transactions(symbol)

    # ── HTML export ───────────────────────────────────────────────────────────

    def build_export_data(self, symbol: str) -> dict:
        """Collect all data needed for an HTML report in one call."""
        info = self.get_info(symbol)
        return {
            "info": info,
            "ratios": self.get_key_ratios(info).to_display_dict(),
            "price_history": self.get_price_history(symbol, period="1mo"),
        }
