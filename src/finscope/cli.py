"""CLI entry point — Command Pattern.

Each menu option is a discrete ``Command`` object with a single
``execute(ctx)`` method.  A ``CommandRegistry`` maps integer keys to command
instances.  The main loop just dispatches to the registry — it never
contains business logic itself.

This eliminates the giant if/elif chain and makes each feature independently
testable and extendable without modifying existing code (Open/Closed
Principle).

The CLI is just **one consumer** of the ``finscope`` library.  All data
access goes through the same :class:`finscope.Stock` class that end-users
import in their own scripts.
"""

from __future__ import annotations

import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from rich.console import Console
from rich.prompt import IntPrompt, Prompt
from rich.rule import Rule

from finscope.exceptions import DataFetchError, TickerNotFoundError
from finscope.services import FundAnalysisService, StockAnalysisService
from finscope.stock import Stock
from finscope.ui import (
    export_to_html,
    make_sparkline,
    render_analyst_recommendations,
    render_comparison,
    render_description,
    render_detailed_financials,
    render_financials,
    render_fund_returns,
    render_global_fund_detail,
    render_global_fund_snapshot,
    render_header,
    render_india_fund_overview,
    render_india_fund_search_results,
    render_insider_transactions,
    render_major_holders,
    render_news,
    render_price_history,
    render_ratios,
    render_sec_filings,
    render_watchlist,
)

console = Console()


# ── Context ────────────────────────────────────────────────────────────────────


@dataclass
class DashboardContext:
    """Shared state passed to every command during a CLI session.

    Wraps a :class:`finscope.Stock` object — the same class library users
    get when they call ``finscope.stock("AAPL")``.
    """

    stock: Stock
    fund_service: FundAnalysisService

    # ── Convenience aliases ──────────────────────────────────────────────────

    @property
    def symbol(self) -> str:
        return self.stock.symbol

    @property
    def info(self) -> dict:
        return self.stock.info

    @property
    def sparkline(self) -> list[float]:
        return self.stock.sparkline


# ── Command base class ────────────────────────────────────────────────────────


class DashboardCommand(ABC):
    """Abstract base for menu commands (Command Pattern)."""

    @abstractmethod
    def execute(self, ctx: DashboardContext) -> None:
        """Run this command using data from *ctx*."""

    def __repr__(self) -> str:  # pragma: no cover
        return f"<{self.__class__.__name__}>"


# ── Concrete commands ─────────────────────────────────────────────────────────


class OverviewCommand(DashboardCommand):
    """Show company overview panel and description."""

    def execute(self, ctx: DashboardContext) -> None:
        render_header(ctx.info, ctx.sparkline)
        render_description(ctx.info)


class KeyRatiosCommand(DashboardCommand):
    """Show key financial ratios."""

    def execute(self, ctx: DashboardContext) -> None:
        ratios = ctx.stock.ratios.to_display_dict()
        render_ratios(ratios)


class PriceHistoryCommand(DashboardCommand):
    """Show price history with sparkline for a user-chosen period."""

    def execute(self, ctx: DashboardContext) -> None:
        period = Prompt.ask(
            "Period",
            choices=["1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "max"],
            default="1mo",
        )
        df = ctx.stock.price_history(period)
        sparkline = ctx.stock._service.get_sparkline(ctx.symbol, period=period)
        render_price_history(df, period, sparkline)


class IncomeStatementCommand(DashboardCommand):
    def execute(self, ctx: DashboardContext) -> None:
        render_financials(ctx.stock.financials, "Income Statement")


class BalanceSheetCommand(DashboardCommand):
    def execute(self, ctx: DashboardContext) -> None:
        render_financials(ctx.stock.balance_sheet, "Balance Sheet")


class CashFlowCommand(DashboardCommand):
    def execute(self, ctx: DashboardContext) -> None:
        render_financials(ctx.stock.cashflow, "Cash Flow Statement")


class NewsCommand(DashboardCommand):
    def execute(self, ctx: DashboardContext) -> None:
        render_news(ctx.stock.news)


class AnalystRecsCommand(DashboardCommand):
    def execute(self, ctx: DashboardContext) -> None:
        render_analyst_recommendations(ctx.stock.analyst_recommendations)


class MajorHoldersCommand(DashboardCommand):
    def execute(self, ctx: DashboardContext) -> None:
        breakdown, institutional = ctx.stock.holders
        render_major_holders(breakdown, institutional)


class SecDetailedFinancialsCommand(DashboardCommand):
    _CAT_MAP = {
        "income": "Income Statement",
        "comprehensive": "Comprehensive Income",
        "assets": "Balance Sheet (Assets)",
        "liabilities": "Balance Sheet (Liabilities & Equity)",
        "cashflow": "Cash Flow",
        "pershare": "Per Share & Shares",
        "debt": "Debt Maturity Schedule",
    }

    def execute(self, ctx: DashboardContext) -> None:
        console.print("Loading detailed financials from SEC EDGAR...")
        edgar_data = ctx.stock.sec_financials
        if not edgar_data:
            console.print("[red]No SEC EDGAR data found for this ticker.[/red]")
            return
        sub = Prompt.ask(
            "Category",
            choices=list(self._CAT_MAP),
            default="income",
        )
        render_detailed_financials(edgar_data, self._CAT_MAP[sub])


class SecFilingsCommand(DashboardCommand):
    def execute(self, ctx: DashboardContext) -> None:
        console.print("Loading recent SEC filings...")
        filings = ctx.stock.sec_filings(count=20)
        render_sec_filings(filings)


class InsiderTransactionsCommand(DashboardCommand):
    def execute(self, ctx: DashboardContext) -> None:
        console.print("Loading insider transactions...")
        render_insider_transactions(ctx.stock.insider_transactions)


class CompareStocksCommand(DashboardCommand):
    def execute(self, ctx: DashboardContext) -> None:
        input_str = Prompt.ask(
            "Enter tickers to compare (comma-separated, e.g., AAPL,MSFT,GOOGL)"
        )
        symbols = [s.strip().upper() for s in input_str.split(",") if s.strip()]
        if ctx.symbol not in symbols:
            symbols.insert(0, ctx.symbol)
        if len(symbols) < 2:
            console.print("[red]Please enter at least 2 tickers.[/red]")
            return
        console.print(f"Loading comparison data for {', '.join(symbols)}...")
        comp_data = ctx.stock.compare_with(*symbols[1:])
        render_comparison([vars(d) for d in comp_data])


class WatchlistCommand(DashboardCommand):
    def execute(self, ctx: DashboardContext) -> None:
        input_str = Prompt.ask(
            "Enter watchlist tickers (comma-separated, e.g., AAPL,TSLA,NVDA)"
        )
        symbols = [s.strip().upper() for s in input_str.split(",") if s.strip()]
        if not symbols:
            console.print("[red]Please enter at least 1 ticker.[/red]")
            return
        console.print(f"Loading watchlist for {', '.join(symbols)}...")
        import finscope
        watch_data = finscope.compare(*symbols)
        render_watchlist([vars(d) for d in watch_data])


class ExportHtmlCommand(DashboardCommand):
    def execute(self, ctx: DashboardContext) -> None:
        filename = Prompt.ask(
            "Output filename", default=f"{ctx.symbol.lower()}_report.html"
        )
        path = ctx.stock.export_html(filename)
        console.print(f"\n[bold green]Report exported to {path}[/bold green]")


class MutualFundsCommand(DashboardCommand):
    """Launches the mutual funds sub-menu."""

    def execute(self, ctx: DashboardContext) -> None:
        _run_mutual_funds_menu(ctx.fund_service)


class ChangeTickerCommand(DashboardCommand):
    """Signals the main loop to ask for a new ticker symbol.

    The main loop checks ``isinstance(command, ChangeTickerCommand)`` and
    returns ``True`` to trigger a ticker change instead of calling ``execute``.
    This ``execute`` implementation is a no-op safety fallback.
    """

    def execute(self, ctx: DashboardContext) -> None:  # pragma: no cover
        pass  # Handled as a sentinel in the main loop; never called directly.


# ── Command Registry ──────────────────────────────────────────────────────────


class CommandRegistry:
    """Maps integer menu keys to (label, DashboardCommand) pairs."""

    def __init__(self) -> None:
        self._commands: dict[int, tuple[str, DashboardCommand | None]] = {}

    def register(
        self, key: int, label: str, command: DashboardCommand | None = None
    ) -> "CommandRegistry":
        self._commands[key] = (label, command)
        return self

    def get(self, key: int) -> DashboardCommand | None:
        entry = self._commands.get(key)
        return entry[1] if entry else None

    def label(self, key: int) -> str:
        entry = self._commands.get(key)
        return entry[0] if entry else ""

    def items(self) -> list[tuple[int, str]]:
        return [(k, label) for k, (label, _) in self._commands.items()]


def _build_registry() -> CommandRegistry:
    """Construct and return the main command registry."""
    return (
        CommandRegistry()
        .register(1,  "Company Overview",                     OverviewCommand())
        .register(2,  "Key Ratios",                           KeyRatiosCommand())
        .register(3,  "Price History (with sparkline)",       PriceHistoryCommand())
        .register(4,  "Income Statement (Yahoo)",             IncomeStatementCommand())
        .register(5,  "Balance Sheet (Yahoo)",                BalanceSheetCommand())
        .register(6,  "Cash Flow (Yahoo)",                    CashFlowCommand())
        .register(7,  "News",                                 NewsCommand())
        .register(8,  "Analyst Recommendations",              AnalystRecsCommand())
        .register(9,  "Major Holders",                        MajorHoldersCommand())
        .register(10, "SEC EDGAR: Detailed Financials (XBRL)",SecDetailedFinancialsCommand())
        .register(11, "SEC EDGAR: Recent Filings",            SecFilingsCommand())
        .register(12, "SEC EDGAR: Insider Transactions",      InsiderTransactionsCommand())
        .register(13, "Compare Stocks",                       CompareStocksCommand())
        .register(14, "Watchlist",                            WatchlistCommand())
        .register(15, "Export Report to HTML",                ExportHtmlCommand())
        .register(16, "Mutual Funds",                         MutualFundsCommand())
        .register(17, "Change Ticker",                        ChangeTickerCommand())
        .register(0,  "Exit",                                 None)
    )


_REGISTRY = _build_registry()


def _show_menu() -> None:
    console.print()
    console.print(Rule("Menu", style="blue"))
    for key, label in _REGISTRY.items():
        style = "red" if key == 0 else "cyan"
        console.print(f"  [{style}][{key:>2}][/{style}] {label}")
    console.print()


# ── Mutual Funds sub-menu ─────────────────────────────────────────────────────

_MF_MENU = {
    1: "India — Search & Explore (MFAPI.in)",
    2: "US Mutual Funds Snapshot",
    3: "Global ETF Snapshot (LSE)",
    4: "Asia Pacific ETF Snapshot",
    5: "European ETF Snapshot",
    6: "Fixed Income / Bond ETF Snapshot",
    7: "Lookup Any Fund / ETF by Ticker",
    0: "Back",
}

_REGION_MAP = {
    2: "US",
    3: "Global ETF (LSE)",
    4: "Asia Pacific ETF",
    5: "European ETF",
    6: "Fixed Income / Bond ETF",
}


def _run_mutual_funds_menu(fund_service: FundAnalysisService) -> None:
    while True:
        console.print()
        console.print(Rule("Mutual Funds", style="bold green"))
        for key, label in _MF_MENU.items():
            style = "red" if key == 0 else "cyan"
            console.print(f"  [{style}][{key}][/{style}] {label}")
        console.print()

        choice = IntPrompt.ask("Select", default=0)

        if choice == 0:
            return

        if choice == 1:
            _india_fund_flow(fund_service)

        elif choice in _REGION_MAP:
            region = _REGION_MAP[choice]
            console.print(f"\nLoading {region} funds...")
            data = fund_service.get_popular_funds_snapshot(region)
            render_global_fund_snapshot(data, region)

        elif choice == 7:
            sym = Prompt.ask("Enter fund/ETF ticker (e.g., VWRL.L, INDA, AGG)")
            if not sym.strip():
                continue
            sym = sym.strip().upper()
            console.print(f"Loading data for {sym}...")
            import finscope
            f = finscope.fund(sym)
            if not f.info:
                console.print(f"[red]Could not find fund: {sym}[/red]")
                continue
            render_global_fund_detail(sym, f.info, f.returns, f.sparkline)

        else:
            console.print("[red]Invalid option.[/red]")


def _india_fund_flow(fund_service: FundAnalysisService) -> None:
    while True:
        console.print()
        console.print(Rule("Indian Mutual Funds  (MFAPI.in — 37,500+ funds)", style="green"))
        console.print("  [cyan][1][/cyan] Search by name")
        console.print("  [cyan][2][/cyan] Look up by scheme code")
        console.print("  [red][0][/red] Back")
        console.print()

        sub = IntPrompt.ask("Select", default=0)

        if sub == 0:
            return

        if sub == 1:
            query = Prompt.ask("Search (e.g., SBI Small Cap, Parag Parikh)")
            if not query.strip():
                continue
            results = fund_service.search_india_funds(query.strip())
            render_india_fund_search_results(results)
            if results:
                code = Prompt.ask("Enter scheme code to view details (or press Enter to skip)", default="")
                if code.strip():
                    _show_india_fund(fund_service, code.strip())

        elif sub == 2:
            code = Prompt.ask("Enter scheme code (e.g., 125497)")
            if code.strip():
                _show_india_fund(fund_service, code.strip())


def _show_india_fund(fund_service: FundAnalysisService, scheme_code: str) -> None:
    console.print(f"\nLoading scheme {scheme_code}...")
    detail = fund_service.get_india_fund_detail(scheme_code)

    if not detail:
        console.print(f"[red]Could not fetch fund {scheme_code}.[/red]")
        return

    meta = detail.get("meta", {})
    nav_data = detail.get("data", [])

    render_india_fund_overview(meta, {}, nav_data)

    returns = fund_service.calculate_india_fund_returns(nav_data)
    render_fund_returns(returns, title="Point-to-Point Returns")

    spark_vals = fund_service.get_india_fund_nav_series(nav_data, days=365)
    if spark_vals:
        console.print(f"  1Y NAV Trend: {make_sparkline(spark_vals, width=60)}")


# ── Main loop ─────────────────────────────────────────────────────────────────


def run_dashboard(
    symbol: str,
    stock_service: StockAnalysisService | None = None,
    fund_service: FundAnalysisService | None = None,
) -> bool:
    """Run the interactive CLI for *symbol*.

    Returns ``True`` when the user selects "Change Ticker", ``False`` on exit.
    """
    _stock_svc = stock_service or StockAnalysisService()
    _fund_svc = fund_service or FundAnalysisService()

    console.print(f"\nLoading data for [bold cyan]{symbol.upper()}[/bold cyan]...\n")

    try:
        s = Stock(symbol, service=_stock_svc)
        _ = s.info  # Trigger the initial fetch — validates the ticker
    except TickerNotFoundError:
        console.print(f"[red]Could not find ticker: {symbol}[/red]")
        return False
    except DataFetchError as exc:
        console.print(f"[red]{exc}[/red]")
        return False

    render_header(s.info, s.sparkline)

    ctx = DashboardContext(stock=s, fund_service=_fund_svc)

    while True:
        _show_menu()
        choice = IntPrompt.ask("Select an option", default=1)

        if choice == 0:
            console.print("[dim]Goodbye.[/dim]")
            sys.exit(0)

        command = _REGISTRY.get(choice)

        if command is None and choice != 0:
            console.print("[red]Invalid option.[/red]")
            continue

        if isinstance(command, ChangeTickerCommand):
            return True

        if command is not None:
            try:
                command.execute(ctx)
            except (TickerNotFoundError, DataFetchError) as exc:
                console.print(f"[red]{exc}[/red]")
            except KeyboardInterrupt:
                console.print("\n[dim]Cancelled.[/dim]")


# ── CLI entry point ───────────────────────────────────────────────────────────


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Finscope — terminal-based financial research tool."
    )
    parser.add_argument("symbol", nargs="?", help="Stock ticker symbol (e.g., AAPL, MSFT)")
    args = parser.parse_args()

    console.print(Rule("Finscope", style="bold blue"))
    console.print(
        "[dim]A terminal-based financial research tool powered by Yahoo Finance, SEC EDGAR, and Rich[/dim]\n"
    )

    while True:
        if args.symbol:
            symbol = args.symbol
            args.symbol = None
        else:
            symbol = Prompt.ask("Enter a stock ticker (e.g., AAPL, TSLA, MSFT)")

        if not symbol.strip():
            console.print("[red]Please enter a valid ticker.[/red]")
            continue

        change_ticker = run_dashboard(symbol.strip().upper())
        if not change_ticker:
            break


if __name__ == "__main__":
    main()
