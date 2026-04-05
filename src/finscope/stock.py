"""High-level ``Stock`` and ``Fund`` classes — the primary library entry points.

These classes wrap the service layer behind a clean, ergonomic API built for
interactive use (REPL, Jupyter notebooks) as well as scripting.

All data properties are **lazily fetched and cached** on first access using
``functools.cached_property``.  Nothing hits the network until you ask for it.

Example::

    import finscope

    # ── Stocks ────────────────────────────────────────────────────────────────
    aapl = finscope.stock("AAPL")

    aapl.info                        # raw Yahoo Finance dict
    aapl.ratios.pe_ratio             # 28.5
    aapl.ratios.market_cap           # 2_700_000_000_000
    aapl.price_history("1y")         # OHLCV DataFrame
    aapl.sparkline                   # [100.0, 105.0, …]
    aapl.news                        # list of article dicts
    aapl.financials                  # income statement DataFrame
    aapl.balance_sheet
    aapl.cashflow
    aapl.analyst_recommendations
    aapl.holders
    aapl.sec_financials              # XBRL data from SEC EDGAR
    aapl.sec_filings(count=10)
    aapl.insider_transactions
    aapl.compare_with("MSFT", "GOOGL")  # list[ComparisonData]
    aapl.export_html("report.html")

    # ── Global ETFs / Funds ───────────────────────────────────────────────────
    vwrl = finscope.fund("VWRL.L")
    vwrl.info
    vwrl.returns
    vwrl.sparkline
"""

from __future__ import annotations

from functools import cached_property
from typing import TYPE_CHECKING

import pandas as pd

from finscope.models import ComparisonData, KeyRatios

if TYPE_CHECKING:
    from finscope.services.fund_service import FundAnalysisService
    from finscope.services.stock_service import StockAnalysisService


__all__ = ["Stock", "Fund"]


# ── Stock ─────────────────────────────────────────────────────────────────────


class Stock:
    """A single equity — the primary finscope library entry point.

    Instantiate via :func:`finscope.stock` rather than directly::

        import finscope
        aapl = finscope.stock("AAPL")

    Args:
        symbol:  Ticker symbol (case-insensitive; stored as upper-case).
        service: Optional pre-configured ``StockAnalysisService``.  A
                 default instance is created when not supplied.
    """

    def __init__(self, symbol: str, service: "StockAnalysisService | None" = None) -> None:
        from finscope.services.stock_service import StockAnalysisService

        self._symbol: str = symbol.upper()
        self._service: StockAnalysisService = service or StockAnalysisService()

    # ── Identity ──────────────────────────────────────────────────────────────

    @property
    def symbol(self) -> str:
        """Upper-cased ticker symbol."""
        return self._symbol

    # ── Lazy data properties ──────────────────────────────────────────────────

    @cached_property
    def info(self) -> dict:
        """Raw metadata dict from Yahoo Finance.

        Raises:
            TickerNotFoundError: if the symbol is not recognised.
            DataFetchError: on network failures.
        """
        return self._service.get_info(self._symbol)

    @cached_property
    def ratios(self) -> KeyRatios:
        """Key financial ratios derived from :attr:`info`."""
        return self._service.get_key_ratios(self.info)

    @cached_property
    def sparkline(self) -> list[float]:
        """3-month closing-price series (oldest → newest) for trend charts."""
        return self._service.get_sparkline(self._symbol, period="3mo")

    def price_history(self, period: str = "1mo") -> pd.DataFrame:
        """OHLCV price history DataFrame.

        Args:
            period: Any yfinance period string: ``1d``, ``5d``, ``1mo``,
                    ``3mo``, ``6mo``, ``1y``, ``2y``, ``5y``, ``ytd``, ``max``.
        """
        return self._service.get_price_history(self._symbol, period)

    @cached_property
    def news(self) -> list[dict]:
        """Recent news article dicts."""
        return self._service.get_news(self._symbol)

    @cached_property
    def financials(self) -> pd.DataFrame:
        """Annual income statement as a DataFrame."""
        return self._service.get_financials(self._symbol)

    @cached_property
    def balance_sheet(self) -> pd.DataFrame:
        """Annual balance sheet as a DataFrame."""
        return self._service.get_balance_sheet(self._symbol)

    @cached_property
    def cashflow(self) -> pd.DataFrame:
        """Annual cash flow statement as a DataFrame."""
        return self._service.get_cashflow(self._symbol)

    @cached_property
    def analyst_recommendations(self) -> pd.DataFrame | None:
        """Analyst buy / sell / hold recommendation counts, or ``None``."""
        return self._service.get_analyst_recommendations(self._symbol)

    @cached_property
    def holders(self) -> tuple[pd.DataFrame | None, pd.DataFrame | None]:
        """``(breakdown, institutional_holders)`` DataFrames."""
        return self._service.get_major_holders(self._symbol)

    @cached_property
    def sec_financials(self) -> dict:
        """Detailed XBRL financials from SEC EDGAR, organised by category."""
        return self._service.get_detailed_financials(self._symbol)

    def sec_filings(self, count: int = 20) -> list[dict]:
        """Recent SEC filings (10-K, 10-Q, 8-K, …).

        Args:
            count: Maximum number of filings to return.
        """
        return self._service.get_recent_filings(self._symbol, count=count)

    @cached_property
    def insider_transactions(self) -> list[dict]:
        """Form 3 / 4 / 5 insider transaction filings."""
        return self._service.get_insider_transactions(self._symbol)

    # ── Multi-stock operations ────────────────────────────────────────────────

    def compare_with(self, *symbols: str) -> list[ComparisonData]:
        """Return side-by-side comparison data for this stock and *symbols*.

        Example::

            aapl.compare_with("MSFT", "GOOGL")
        """
        all_symbols = [self._symbol] + [s.upper() for s in symbols]
        return self._service.get_comparison_data(all_symbols)

    # ── Export ────────────────────────────────────────────────────────────────

    def export_html(self, path: str | None = None) -> str:
        """Export a fundamental report to an HTML file.

        Args:
            path: Output file path.  Defaults to ``<symbol>_report.html``.

        Returns:
            The resolved output path.
        """
        from finscope.ui import export_to_html

        output_path = path or f"{self._symbol.lower()}_report.html"
        data = self._service.build_export_data(self._symbol)
        export_to_html(
            data["info"],
            data["ratios"],
            data["price_history"],
            output_path=output_path,
        )
        return output_path

    # ── AI-powered analysis (requires API key) ────────────────────────────────

    def dividends(self) -> "DividendAnalysis":
        """Dividend analysis: history, growth, payout ratio, DRIP simulation."""
        from finscope.dividends import analyze_dividends
        return analyze_dividends(self._symbol, stock=self)

    def earnings(self) -> "EarningsAnalysis":
        """Earnings analysis: surprise history, beat rate, next date."""
        from finscope.earnings import analyze_earnings
        return analyze_earnings(self._symbol, stock=self)

    def peers(self, max_peers: int = 8) -> "PeerComparison":
        """Auto-discover sector peers and compare multiples."""
        from finscope.peers import discover_peers
        return discover_peers(self._symbol, max_peers=max_peers, stock=self)

    def valuate(self) -> "StockValuation":
        """Run all valuation models — pure financial logic, no AI needed.

        Runs Graham Number, DCF, PEG fair value, relative valuation,
        Piotroski F-Score, and Altman Z-Score, then combines into a
        composite verdict.

        Returns:
            A :class:`~finscope.valuation.models.StockValuation`.

        Example::

            v = aapl.valuate()
            v.verdict              # "Fairly Valued"
            v.margin_of_safety     # -5.2%
            v.graham.intrinsic     # 112.45
            v.piotroski.score      # 7
        """
        from finscope.valuation import valuate
        return valuate(self._symbol)

    def risk(self, period: str = "1y") -> "StockRisk":
        """Compute a comprehensive risk profile — pure financial math, no AI needed.

        Computes volatility, VaR/CVaR, max drawdown, Sharpe/Sortino/Calmar,
        beta vs S&P 500, and fundamental balance-sheet risk.

        Args:
            period: Look-back window for price history (default ``"1y"``).

        Returns:
            A :class:`~finscope.risk.models.StockRisk`.

        Example::

            r = aapl.risk()
            r.risk_level                  # "Moderate"
            r.volatility.annual_vol       # 0.24
            r.downside.max_drawdown       # -0.31
            r.risk_adjusted.sharpe_ratio  # 1.12
            r.market.beta                 # 1.24
        """
        from finscope.risk import compute_risk
        return compute_risk(self._symbol, period=period, stock=self)

    async def analyze(self) -> "StockAnalysis":
        """Run a comprehensive AI analysis of this stock.

        Requires an LLM provider API key in the environment.
        See :mod:`finscope.ai` for details.

        Returns:
            A :class:`~finscope.ai.models.StockAnalysis` with summary,
            bull/bear cases, risk factors, and sentiment.

        Example::

            analysis = await aapl.analyze()
            print(analysis.summary)
            print(analysis.sentiment)  # 'Bullish', 'Neutral', etc.
        """
        from finscope.ai import analyze_stock
        return await analyze_stock(self._symbol)

    async def ask(self, question: str) -> str:
        """Ask any question about this stock — the AI fetches data as needed.

        Args:
            question: Natural language question.

        Returns:
            The AI agent's response.

        Example::

            answer = await aapl.ask("What's Apple's debt situation?")
        """
        from finscope.ai import ask_stock
        return await ask_stock(self._symbol, question)

    async def summarize_filings(self) -> "FilingSummary":
        """AI-powered summary of recent SEC filings.

        Returns:
            A :class:`~finscope.ai.models.FilingSummary` with key
            highlights, risk factors, and management outlook.
        """
        from finscope.ai import summarize_filings
        return await summarize_filings(self._symbol)

    # ── Dunder helpers ────────────────────────────────────────────────────────

    def __repr__(self) -> str:
        try:
            price = self.info.get("currentPrice") or self.info.get("regularMarketPrice", "?")
            name = self.info.get("shortName", self._symbol)
            currency = self.info.get("currency", "USD")
            return f"Stock('{self._symbol}' | {name} | {currency} {price})"
        except Exception:
            return f"Stock('{self._symbol}')"

    def __str__(self) -> str:
        return self.__repr__()

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Stock):
            return self._symbol == other._symbol
        return NotImplemented

    def __hash__(self) -> int:
        return hash(self._symbol)


# ── Fund ──────────────────────────────────────────────────────────────────────


class Fund:
    """A global ETF or mutual fund — fetched via Yahoo Finance.

    Instantiate via :func:`finscope.fund`::

        import finscope
        vwrl = finscope.fund("VWRL.L")
        vwrl.info
        vwrl.returns
        vwrl.sparkline

    Args:
        symbol:  Yahoo Finance ticker (e.g. ``"VWRL.L"``, ``"INDA"``, ``"AGG"``).
        service: Optional pre-configured ``FundAnalysisService``.
    """

    def __init__(self, symbol: str, service: "FundAnalysisService | None" = None) -> None:
        from finscope.services.fund_service import FundAnalysisService

        self._symbol: str = symbol.upper()
        self._service: FundAnalysisService = service or FundAnalysisService()

    # ── Identity ──────────────────────────────────────────────────────────────

    @property
    def symbol(self) -> str:
        return self._symbol

    # ── Lazy data properties ──────────────────────────────────────────────────

    @cached_property
    def info(self) -> dict | None:
        """Raw Yahoo Finance info dict, or ``None`` if not found."""
        return self._service.get_global_fund_info(self._symbol)

    @cached_property
    def returns(self) -> dict:
        """Calculated historical returns keyed by period label."""
        return self._service.get_global_fund_returns(self._symbol)

    @cached_property
    def sparkline(self) -> list[float]:
        """1-year closing-price series for trend charts."""
        return self._service.get_global_fund_sparkline(self._symbol, period="1y")

    def risk(self, period: str = "1y") -> "FundRisk":
        """Compute a risk profile from NAV/price history.

        Covers volatility, VaR/CVaR, max drawdown, Sharpe/Sortino/Calmar,
        and beta vs SPY (for global ETFs).
        """
        from finscope.fund_analysis import analyze_global_fund
        risk_result, _ = analyze_global_fund(self._symbol, fund=self, period=period)
        return risk_result

    def analyze(self) -> "FundAnalysis":
        """Fund-specific analysis: expense ratio, rolling returns, return consistency."""
        from finscope.fund_analysis import analyze_global_fund
        _, analysis = analyze_global_fund(self._symbol, fund=self)
        return analysis

    # ── Dunder helpers ────────────────────────────────────────────────────────

    def __repr__(self) -> str:
        try:
            name = (self.info or {}).get("shortName", self._symbol)
            return f"Fund('{self._symbol}' | {name})"
        except Exception:
            return f"Fund('{self._symbol}')"

    def __str__(self) -> str:
        return self.__repr__()

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Fund):
            return self._symbol == other._symbol
        return NotImplemented

    def __hash__(self) -> int:
        return hash(self._symbol)
