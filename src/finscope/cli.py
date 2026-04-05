"""CLI entry point — direct subcommands + opt-in interactive mode.

Direct commands (default)::

    finscope AAPL                       # quick overview
    finscope AAPL ratios                # key ratios
    finscope AAPL price 1y              # price history
    finscope AAPL news                  # recent news
    finscope compare AAPL MSFT GOOGL    # side-by-side
    finscope watchlist AAPL TSLA NVDA   # compact watchlist
    finscope export AAPL                # HTML report
    finscope funds                      # mutual funds (interactive sub-menu)

Interactive mode (opt-in)::

    finscope AAPL -i          # menu loop for AAPL
    finscope -i               # prompts for ticker, then menu

Architecture: the CLI is just a thin consumer of the ``finscope`` library.
All data flows through :class:`finscope.Stock`.
"""

from __future__ import annotations

import argparse
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass

from rich.console import Console
from rich.prompt import IntPrompt, Prompt
from rich.rule import Rule

import finscope as fs
from finscope.exceptions import DataFetchError, FinScopeError, TickerNotFoundError
from finscope.services import FundAnalysisService
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

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  DIRECT CLI COMMANDS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Top-level keywords that are NOT ticker symbols
_KEYWORDS = {"compare", "watchlist", "export", "funds"}

# Valid stock sub-commands
_STOCK_SUBCOMMANDS = {
    "ratios", "price", "financials", "balance-sheet", "cashflow",
    "news", "analysts", "holders", "sec-financials", "sec-filings",
    "insiders", "overview",
}

_SEC_CAT_MAP = {
    "income": "Income Statement",
    "comprehensive": "Comprehensive Income",
    "assets": "Balance Sheet (Assets)",
    "liabilities": "Balance Sheet (Liabilities & Equity)",
    "cashflow": "Cash Flow",
    "pershare": "Per Share & Shares",
    "debt": "Debt Maturity Schedule",
}


def _load_stock(symbol: str) -> Stock:
    """Create and validate a Stock object, printing a loading message."""
    console.print(f"\nLoading [bold cyan]{symbol.upper()}[/bold cyan]...\n")
    s = fs.stock(symbol)
    _ = s.info  # trigger fetch to validate ticker
    return s


def cmd_overview(symbol: str) -> None:
    """Quick overview: header + description + ratios."""
    s = _load_stock(symbol)
    render_header(s.info, s.sparkline)
    render_description(s.info)
    render_ratios(s.ratios.to_display_dict())


def cmd_ratios(symbol: str) -> None:
    s = _load_stock(symbol)
    render_header(s.info, s.sparkline)
    render_ratios(s.ratios.to_display_dict())


def cmd_price(symbol: str, period: str = "1mo") -> None:
    s = _load_stock(symbol)
    df = s.price_history(period)
    sparkline = s._service.get_sparkline(symbol, period=period)
    render_price_history(df, period, sparkline)


def cmd_financials(symbol: str) -> None:
    s = _load_stock(symbol)
    render_financials(s.financials, "Income Statement")


def cmd_balance_sheet(symbol: str) -> None:
    s = _load_stock(symbol)
    render_financials(s.balance_sheet, "Balance Sheet")


def cmd_cashflow(symbol: str) -> None:
    s = _load_stock(symbol)
    render_financials(s.cashflow, "Cash Flow Statement")


def cmd_news(symbol: str) -> None:
    s = _load_stock(symbol)
    render_header(s.info, s.sparkline)
    render_news(s.news)


def cmd_analysts(symbol: str) -> None:
    s = _load_stock(symbol)
    render_header(s.info, s.sparkline)
    render_analyst_recommendations(s.analyst_recommendations)


def cmd_holders(symbol: str) -> None:
    s = _load_stock(symbol)
    breakdown, institutional = s.holders
    render_major_holders(breakdown, institutional)


def cmd_sec_financials(symbol: str, category: str = "income") -> None:
    s = _load_stock(symbol)
    cat_label = _SEC_CAT_MAP.get(category, "Income Statement")
    edgar_data = s.sec_financials
    if not edgar_data:
        console.print("[red]No SEC EDGAR data found for this ticker.[/red]")
        return
    render_detailed_financials(edgar_data, cat_label)


def cmd_sec_filings(symbol: str) -> None:
    s = _load_stock(symbol)
    render_sec_filings(s.sec_filings(count=20))


def cmd_insiders(symbol: str) -> None:
    s = _load_stock(symbol)
    render_insider_transactions(s.insider_transactions)


def cmd_compare(symbols: list[str]) -> None:
    if len(symbols) < 2:
        console.print("[red]Please provide at least 2 tickers to compare.[/red]")
        return
    console.print(f"\nComparing [bold cyan]{', '.join(symbols)}[/bold cyan]...\n")
    data = fs.compare(*symbols)
    render_comparison([vars(d) for d in data])


def cmd_watchlist(symbols: list[str]) -> None:
    if not symbols:
        console.print("[red]Please provide at least 1 ticker.[/red]")
        return
    console.print(f"\nLoading watchlist for [bold cyan]{', '.join(symbols)}[/bold cyan]...\n")
    data = fs.compare(*symbols)
    render_watchlist([vars(d) for d in data])


def cmd_export(symbol: str, output: str | None = None) -> None:
    s = _load_stock(symbol)
    path = s.export_html(output)
    console.print(f"\n[bold green]✓ Report exported to {path}[/bold green]")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  INTERACTIVE MODE (opt-in with -i)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@dataclass
class DashboardContext:
    """Shared state for the interactive menu session."""

    stock: Stock
    fund_service: FundAnalysisService

    @property
    def symbol(self) -> str:
        return self.stock.symbol

    @property
    def info(self) -> dict:
        return self.stock.info

    @property
    def sparkline(self) -> list[float]:
        return self.stock.sparkline


class DashboardCommand(ABC):
    """Abstract base for interactive menu commands (Command Pattern)."""

    @abstractmethod
    def execute(self, ctx: DashboardContext) -> None:
        ...

    def __repr__(self) -> str:  # pragma: no cover
        return f"<{self.__class__.__name__}>"


# ── Concrete commands ─────────────────────────────────────────────────────────

class OverviewCommand(DashboardCommand):
    def execute(self, ctx: DashboardContext) -> None:
        render_header(ctx.info, ctx.sparkline)
        render_description(ctx.info)


class KeyRatiosCommand(DashboardCommand):
    def execute(self, ctx: DashboardContext) -> None:
        render_ratios(ctx.stock.ratios.to_display_dict())


class PriceHistoryCommand(DashboardCommand):
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
    def execute(self, ctx: DashboardContext) -> None:
        console.print("Loading detailed financials from SEC EDGAR...")
        edgar_data = ctx.stock.sec_financials
        if not edgar_data:
            console.print("[red]No SEC EDGAR data found for this ticker.[/red]")
            return
        sub = Prompt.ask("Category", choices=list(_SEC_CAT_MAP), default="income")
        render_detailed_financials(edgar_data, _SEC_CAT_MAP[sub])


class SecFilingsCommand(DashboardCommand):
    def execute(self, ctx: DashboardContext) -> None:
        console.print("Loading recent SEC filings...")
        render_sec_filings(ctx.stock.sec_filings(count=20))


class InsiderTransactionsCommand(DashboardCommand):
    def execute(self, ctx: DashboardContext) -> None:
        console.print("Loading insider transactions...")
        render_insider_transactions(ctx.stock.insider_transactions)


class CompareStocksCommand(DashboardCommand):
    def execute(self, ctx: DashboardContext) -> None:
        input_str = Prompt.ask("Enter tickers (comma-separated, e.g., AAPL,MSFT,GOOGL)")
        symbols = [s.strip().upper() for s in input_str.split(",") if s.strip()]
        if ctx.symbol not in symbols:
            symbols.insert(0, ctx.symbol)
        if len(symbols) < 2:
            console.print("[red]Please enter at least 2 tickers.[/red]")
            return
        console.print(f"Loading comparison for {', '.join(symbols)}...")
        data = ctx.stock.compare_with(*symbols[1:])
        render_comparison([vars(d) for d in data])


class WatchlistCommand(DashboardCommand):
    def execute(self, ctx: DashboardContext) -> None:
        input_str = Prompt.ask("Enter tickers (comma-separated, e.g., AAPL,TSLA,NVDA)")
        symbols = [s.strip().upper() for s in input_str.split(",") if s.strip()]
        if not symbols:
            console.print("[red]Please enter at least 1 ticker.[/red]")
            return
        console.print(f"Loading watchlist for {', '.join(symbols)}...")
        data = fs.compare(*symbols)
        render_watchlist([vars(d) for d in data])


class ExportHtmlCommand(DashboardCommand):
    def execute(self, ctx: DashboardContext) -> None:
        filename = Prompt.ask("Output filename", default=f"{ctx.symbol.lower()}_report.html")
        path = ctx.stock.export_html(filename)
        console.print(f"\n[bold green]✓ Report exported to {path}[/bold green]")


class MutualFundsCommand(DashboardCommand):
    def execute(self, ctx: DashboardContext) -> None:
        _run_mutual_funds_menu(ctx.fund_service)


class ChangeTickerCommand(DashboardCommand):
    """Signals the main loop to ask for a new ticker symbol."""

    def execute(self, ctx: DashboardContext) -> None:  # pragma: no cover
        pass


# ── Command Registry ──────────────────────────────────────────────────────────


class CommandRegistry:
    """Maps integer menu keys to (label, command) pairs."""

    def __init__(self) -> None:
        self._commands: dict[int, tuple[str, DashboardCommand | None]] = {}

    def register(self, key: int, label: str, command: DashboardCommand | None = None) -> "CommandRegistry":
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
            f = fs.fund(sym)
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
                code = Prompt.ask("Enter scheme code (or press Enter to skip)", default="")
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


# ── Interactive loop ──────────────────────────────────────────────────────────


def run_interactive(
    symbol: str,
    stock_service: fs.StockAnalysisService | None = None,
    fund_service: FundAnalysisService | None = None,
) -> bool:
    """Run the interactive menu for *symbol*.

    Returns ``True`` when the user selects "Change Ticker", ``False`` on exit.
    """
    _stock_svc = stock_service or fs.StockAnalysisService()
    _fund_svc = fund_service or FundAnalysisService()

    console.print(f"\nLoading data for [bold cyan]{symbol.upper()}[/bold cyan]...\n")

    try:
        s = Stock(symbol, service=_stock_svc)
        _ = s.info
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


# Keep backward compat name
run_dashboard = run_interactive


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  MAIN ENTRY POINT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_USAGE_EXAMPLES = """
examples:
  finscope AAPL                     Quick overview
  finscope AAPL ratios              Key financial ratios
  finscope AAPL price 1y            Price history (1 year)
  finscope AAPL financials          Income statement
  finscope AAPL balance-sheet       Balance sheet
  finscope AAPL cashflow            Cash flow statement
  finscope AAPL news                Recent news
  finscope AAPL analysts            Analyst recommendations
  finscope AAPL holders             Major holders
  finscope AAPL sec-financials      SEC EDGAR XBRL financials
  finscope AAPL sec-filings         Recent SEC filings
  finscope AAPL insiders            Insider transactions
  finscope compare AAPL MSFT GOOGL  Side-by-side comparison
  finscope watchlist AAPL TSLA NVDA Compact watchlist
  finscope export AAPL              HTML report
  finscope funds                    Mutual funds explorer
  finscope AAPL -i                  Interactive menu mode
"""


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="finscope",
        description="Finscope — terminal-based financial research tool.",
        epilog=_USAGE_EXAMPLES,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "args",
        nargs="*",
        metavar="TICKER|COMMAND",
        help="Ticker symbol or command (compare, watchlist, export, funds)",
    )
    parser.add_argument(
        "-i", "--interactive",
        action="store_true",
        help="Launch interactive menu mode",
    )
    parser.add_argument(
        "-o", "--output",
        help="Output file path (for export command)",
    )
    parser.add_argument(
        "--period",
        default="1mo",
        help="Time period for price history (default: 1mo)",
    )
    parser.add_argument(
        "--category",
        default="income",
        choices=list(_SEC_CAT_MAP),
        help="SEC financials category (default: income)",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"finscope {fs.__version__}",
    )
    return parser


def _dispatch(parsed: argparse.Namespace) -> None:
    """Route parsed CLI args to the right command function."""
    args: list[str] = parsed.args
    interactive: bool = parsed.interactive

    # ── No arguments at all → interactive prompt ──────────────────────────
    if not args and interactive:
        _print_banner()
        while True:
            symbol = Prompt.ask("Enter a stock ticker (e.g., AAPL, TSLA, MSFT)")
            if not symbol.strip():
                console.print("[red]Please enter a valid ticker.[/red]")
                continue
            change = run_interactive(symbol.strip().upper())
            if not change:
                break
        return

    if not args:
        _print_banner()
        console.print("[dim]Run [bold]finscope --help[/bold] for usage, or [bold]finscope -i[/bold] for interactive mode.[/dim]\n")
        return

    first = args[0].lower()

    # ── Top-level keyword commands ────────────────────────────────────────
    if first == "compare":
        symbols = [s.upper() for s in args[1:]]
        cmd_compare(symbols)
        return

    if first == "watchlist":
        symbols = [s.upper() for s in args[1:]]
        cmd_watchlist(symbols)
        return

    if first == "export":
        if len(args) < 2:
            console.print("[red]Usage: finscope export TICKER [--output file.html][/red]")
            return
        cmd_export(args[1].upper(), output=parsed.output)
        return

    if first == "funds":
        _print_banner()
        fund_svc = FundAnalysisService()
        _run_mutual_funds_menu(fund_svc)
        return

    # ── Ticker-based commands ─────────────────────────────────────────────
    symbol = args[0].upper()
    subcommand = args[1].lower() if len(args) > 1 else None

    # -i flag → interactive mode for this ticker
    if interactive:
        _print_banner()
        while True:
            change = run_interactive(symbol)
            if not change:
                break
            symbol = Prompt.ask("Enter a stock ticker").strip().upper()
        return

    # Direct subcommand dispatch
    dispatch = {
        None:             lambda: cmd_overview(symbol),
        "overview":       lambda: cmd_overview(symbol),
        "ratios":         lambda: cmd_ratios(symbol),
        "price":          lambda: cmd_price(symbol, args[2] if len(args) > 2 else parsed.period),
        "financials":     lambda: cmd_financials(symbol),
        "balance-sheet":  lambda: cmd_balance_sheet(symbol),
        "cashflow":       lambda: cmd_cashflow(symbol),
        "news":           lambda: cmd_news(symbol),
        "analysts":       lambda: cmd_analysts(symbol),
        "holders":        lambda: cmd_holders(symbol),
        "sec-financials": lambda: cmd_sec_financials(symbol, parsed.category),
        "sec-filings":    lambda: cmd_sec_filings(symbol),
        "insiders":       lambda: cmd_insiders(symbol),
    }

    handler = dispatch.get(subcommand)
    if handler is None:
        console.print(f"[red]Unknown command: {subcommand}[/red]")
        console.print(f"[dim]Valid commands: {', '.join(sorted(_STOCK_SUBCOMMANDS))}[/dim]")
        return

    handler()


def _print_banner() -> None:
    console.print(Rule("🔭 Finscope", style="bold blue"))
    console.print(
        "[dim]Terminal-based financial research · Yahoo Finance · SEC EDGAR · MFAPI[/dim]\n"
    )


def main() -> None:
    parser = _build_parser()
    parsed = parser.parse_args()

    try:
        _dispatch(parsed)
    except TickerNotFoundError as exc:
        console.print(f"\n[red]✗ {exc}[/red]")
        sys.exit(1)
    except DataFetchError as exc:
        console.print(f"\n[red]✗ {exc}[/red]")
        sys.exit(1)
    except FinScopeError as exc:
        console.print(f"\n[red]✗ {exc}[/red]")
        sys.exit(1)
    except KeyboardInterrupt:
        console.print("\n[dim]Cancelled.[/dim]")
        sys.exit(0)


if __name__ == "__main__":
    main()
