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
from rich.prompt import Prompt
from rich.rule import Rule
import questionary

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
    render_attribution,
)

console = Console()

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  DIRECT CLI COMMANDS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Top-level keywords that are NOT ticker symbols
_KEYWORDS = {"compare", "watchlist", "export", "funds", "screen"}

# Valid stock sub-commands
_STOCK_SUBCOMMANDS = {
    "ratios", "price", "financials", "balance-sheet", "cashflow",
    "news", "analysts", "holders", "sec-financials", "sec-filings",
    "insiders", "overview", "analyze", "ask", "summarize-filings",
    "valuate",
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
    render_attribution("Yahoo Finance")


def cmd_ratios(symbol: str) -> None:
    s = _load_stock(symbol)
    render_header(s.info, s.sparkline)
    render_ratios(s.ratios.to_display_dict())
    render_attribution("Yahoo Finance")


def cmd_price(symbol: str, period: str = "1mo") -> None:
    s = _load_stock(symbol)
    df = s.price_history(period)
    sparkline = s._service.get_sparkline(symbol, period=period)
    render_price_history(df, period, sparkline)
    render_attribution("Yahoo Finance")


def cmd_financials(symbol: str) -> None:
    s = _load_stock(symbol)
    render_financials(s.financials, "Income Statement")
    render_attribution("Yahoo Finance")


def cmd_balance_sheet(symbol: str) -> None:
    s = _load_stock(symbol)
    render_financials(s.balance_sheet, "Balance Sheet")
    render_attribution("Yahoo Finance")


def cmd_cashflow(symbol: str) -> None:
    s = _load_stock(symbol)
    render_financials(s.cashflow, "Cash Flow Statement")
    render_attribution("Yahoo Finance")


def cmd_news(symbol: str) -> None:
    s = _load_stock(symbol)
    render_header(s.info, s.sparkline)
    render_news(s.news)
    render_attribution("Yahoo Finance")


def cmd_analysts(symbol: str) -> None:
    s = _load_stock(symbol)
    render_header(s.info, s.sparkline)
    render_analyst_recommendations(s.analyst_recommendations)
    render_attribution("Yahoo Finance")


def cmd_holders(symbol: str) -> None:
    s = _load_stock(symbol)
    breakdown, institutional = s.holders
    render_major_holders(breakdown, institutional)
    render_attribution("Yahoo Finance")


def cmd_sec_financials(symbol: str, category: str = "income") -> None:
    s = _load_stock(symbol)
    cat_label = _SEC_CAT_MAP.get(category, "Income Statement")
    edgar_data = s.sec_financials
    if not edgar_data:
        console.print("[red]No SEC EDGAR data found for this ticker.[/red]")
        return
    render_detailed_financials(edgar_data, cat_label)
    render_attribution("SEC EDGAR")


def cmd_sec_filings(symbol: str) -> None:
    s = _load_stock(symbol)
    render_sec_filings(s.sec_filings(count=20))
    render_attribution("SEC EDGAR")


def cmd_insiders(symbol: str) -> None:
    s = _load_stock(symbol)
    render_insider_transactions(s.insider_transactions)
    render_attribution("SEC EDGAR")


def cmd_valuate(symbol: str) -> None:
    """Run all valuation models and display the composite verdict."""
    console.print(f"\nRunning valuation models for [bold cyan]{symbol}[/bold cyan]...\n")
    from finscope.valuation import valuate
    v = valuate(symbol)

    console.print(Rule(f"Valuation: {v.symbol}", style="bold magenta"))
    console.print(f"  Current Price: [bold]${v.current_price:.2f}[/bold]" if v.current_price else "")

    # Verdict
    verdict_colors = {
        "Undervalued": "bold green", "Fairly Valued": "yellow",
        "Overvalued": "bold red", "N/A": "dim",
    }
    vc = verdict_colors.get(v.verdict, "white")
    console.print(f"\n  [bold]Verdict:[/bold]  [{vc}]{v.verdict}[/{vc}]")
    console.print(f"  [bold]Confidence:[/bold] {v.confidence}")
    if v.margin_of_safety is not None:
        ms_color = "green" if v.margin_of_safety > 0 else "red"
        console.print(f"  [bold]Margin of Safety:[/bold] [{ms_color}]{v.margin_of_safety:+.1f}%[/{ms_color}]")
    console.print(f"  Signals: [green]{v.signals_bullish} bullish[/green] / "
                  f"[yellow]{v.signals_neutral} neutral[/yellow] / "
                  f"[red]{v.signals_bearish} bearish[/red]\n")

    # Graham Number
    console.print(Rule("Graham Number", style="cyan"))
    g = v.graham
    if g.calculable:
        console.print(f"  EPS: {g.eps:.2f}  |  Book Value: {g.book_value_per_share:.2f}")
        console.print(f"  Intrinsic Value: [bold]${g.intrinsic:.2f}[/bold]")
        ms_c = "green" if g.margin_of_safety_pct and g.margin_of_safety_pct > 0 else "red"
        console.print(f"  Margin of Safety: [{ms_c}]{g.margin_of_safety_pct:+.1f}%[/{ms_c}]  → {g.signal}")
    else:
        console.print("  [dim]Cannot compute (negative EPS or book value)[/dim]")

    # DCF
    console.print(Rule("DCF (Discounted Cash Flow)", style="cyan"))
    d = v.dcf
    if d.calculable:
        console.print(f"  Free Cash Flow: ${d.free_cash_flow/1e9:.2f}B" if d.free_cash_flow else "")
        console.print(f"  Growth Rate: {d.growth_rate*100:.1f}%" if d.growth_rate else "")
        console.print(f"  Discount Rate (WACC): {d.discount_rate*100:.1f}%" if d.discount_rate else "")
        console.print(f"  Intrinsic Value/Share: [bold]${d.intrinsic_per_share:.2f}[/bold]")
        ms_c = "green" if d.margin_of_safety_pct and d.margin_of_safety_pct > 0 else "red"
        console.print(f"  Margin of Safety: [{ms_c}]{d.margin_of_safety_pct:+.1f}%[/{ms_c}]  → {d.signal}")
    else:
        console.print("  [dim]Cannot compute (missing FCF, growth, or share count)[/dim]")

    # PEG Fair Value
    console.print(Rule("PEG Fair Value (Peter Lynch)", style="cyan"))
    p = v.peg
    if p.calculable:
        console.print(f"  EPS: {p.eps:.2f}  |  Growth Rate: {p.earnings_growth_rate:.1f}%")
        console.print(f"  PEG Ratio: {p.peg_ratio:.2f}" if p.peg_ratio else "")
        console.print(f"  Fair Price: [bold]${p.fair_price:.2f}[/bold]")
        ms_c = "green" if p.margin_of_safety_pct and p.margin_of_safety_pct > 0 else "red"
        console.print(f"  Margin of Safety: [{ms_c}]{p.margin_of_safety_pct:+.1f}%[/{ms_c}]  → {p.signal}")
    else:
        console.print(f"  PEG Ratio: {p.peg_ratio:.2f}  → {p.signal}" if p.peg_ratio else "  [dim]Insufficient data[/dim]")

    # Relative
    console.print(Rule("Relative Valuation", style="cyan"))
    r = v.relative
    if r.pe_current:
        console.print(f"  P/E: {r.pe_current:.1f}  |  P/B: {r.pb_current:.1f}" if r.pb_current else f"  P/E: {r.pe_current:.1f}")
    if r.ev_ebitda_current:
        console.print(f"  EV/EBITDA: {r.ev_ebitda_current:.1f}")
    if r.price_vs_50d is not None:
        c = "green" if r.price_vs_50d < 0 else "red"
        console.print(f"  vs 50D Avg: [{c}]{r.price_vs_50d:+.1f}%[/{c}]")
    if r.price_vs_200d is not None:
        c = "green" if r.price_vs_200d < 0 else "red"
        console.print(f"  vs 200D Avg: [{c}]{r.price_vs_200d:+.1f}%[/{c}]")
    if r.price_vs_52w_high is not None:
        console.print(f"  vs 52W High: {r.price_vs_52w_high:+.1f}%")
    console.print(f"  Signal: {r.signal}")

    # Piotroski
    console.print(Rule("Piotroski F-Score", style="cyan"))
    f = v.piotroski
    bar = "\u2588" * f.score + "\u2591" * (9 - f.score)
    score_color = "green" if f.score >= 7 else "yellow" if f.score >= 4 else "red"
    console.print(f"  Score: [{score_color}]{bar} {f.score}/9 ({f.strength})[/{score_color}]")
    for criterion, passed in f.details.items():
        icon = "[green]\u2713[/green]" if passed else "[red]\u2717[/red]"
        console.print(f"    {icon} {criterion}")

    # Altman Z-Score
    console.print(Rule("Altman Z-Score", style="cyan"))
    a = v.altman
    if a.calculable:
        zone_colors = {"Safe": "green", "Grey": "yellow", "Distress": "bold red"}
        zc = zone_colors.get(a.zone, "white")
        console.print(f"  Z-Score: [{zc}]{a.z_score:.2f} ({a.zone} Zone)[/{zc}]")
        for comp, val in a.components.items():
            if val is not None:
                console.print(f"    {comp}: {val:.4f}")
    else:
        console.print("  [dim]Insufficient balance sheet data[/dim]")

    render_attribution("Yahoo Finance, SEC EDGAR")
    console.print()


def cmd_compare(symbols: list[str]) -> None:
    if len(symbols) < 2:
        console.print("[red]Please provide at least 2 tickers to compare.[/red]")
        return
    console.print(f"\nComparing [bold cyan]{', '.join(symbols)}[/bold cyan]...\n")
    data = fs.compare(*symbols)
    render_comparison([vars(d) for d in data])
    render_attribution("Yahoo Finance")


def cmd_watchlist(symbols: list[str]) -> None:
    if not symbols:
        console.print("[red]Please provide at least 1 ticker.[/red]")
        return
    console.print(f"\nLoading watchlist for [bold cyan]{', '.join(symbols)}[/bold cyan]...\n")
    data = fs.compare(*symbols)
    render_watchlist([vars(d) for d in data])
    render_attribution("Yahoo Finance")


def cmd_export(symbol: str, output: str | None = None) -> None:
    s = _load_stock(symbol)
    path = s.export_html(output)
    console.print(f"\n[bold green]✓ Report exported to {path}[/bold green]")


def cmd_screen(query: str) -> None:
    """Run the stock screener with the given query."""
    console.print(f"\n[bold cyan]Screening S&P 500 stocks...[/bold cyan]")
    console.print(f"[dim]Query: {query}[/dim]\n")
    
    from finscope.screener import screen
    results = screen(query)
    
    if not results:
        console.print("[yellow]No stocks matched your criteria.[/yellow]")
        return
        
    from finscope.ui.builders import TableBuilder
    builder = (
        TableBuilder(f"Screener Results ({len(results)} matches)")
        .border("blue")
        .column("Ticker", style="bold cyan")
        .column("Sector")
        .column("Price", justify="right")
        .column("Market Cap", justify="right")
        .column("P/E", justify="right")
        .column("ROE", justify="right")
        .column("Div Yield", justify="right")
    )
    
    for r in results:
        m = r.metrics
        pe_str = f"{m.get('pe'):.1f}" if m.get("pe") else "N/A"
        roe_str = f"{m.get('roe'):.1f}%" if m.get("roe") else "N/A"
        div_str = f"{m.get('dividend_yield'):.2f}%" if m.get("dividend_yield") else "N/A"
        price_str = f"${m.get('current_price'):.2f}" if m.get("current_price") else "N/A"
        
        # Format large market cap
        mcap = m.get("market_cap")
        if mcap:
            if mcap >= 1e12:
                mcap_str = f"${mcap/1e12:.2f}T"
            elif mcap >= 1e9:
                mcap_str = f"${mcap/1e9:.2f}B"
            else:
                mcap_str = f"${mcap/1e6:.2f}M"
        else:
            mcap_str = "N/A"
            
        builder.row(
            r.symbol, 
            m.get("sector") or "N/A", 
            price_str,
            mcap_str,
            pe_str,
            roe_str,
            div_str
        )
        
    console.print(builder.build())
    render_attribution("Yahoo Finance")


# ── AI commands ───────────────────────────────────────────────────────────────

def _require_ai() -> None:
    """Check AI availability and print a helpful error if not configured."""
    from finscope.ai.config import is_ai_available
    if not is_ai_available():
        console.print(
            "\n[red bold]✗ AI features require an LLM provider API key.[/red bold]\n"
            "[dim]Set one of these environment variables:\n"
            "  export OPENAI_API_KEY=sk-...\n"
            "  export ANTHROPIC_API_KEY=sk-ant-...\n"
            "  export GEMINI_API_KEY=...\n"
            "  export GROQ_API_KEY=gsk_...\n"
            "  export MISTRAL_API_KEY=...\n\n"
            "Or set FINSCOPE_AI_MODEL explicitly.[/dim]"
        )
        sys.exit(1)


def _run_async(coro):
    """Run an async coroutine from sync CLI code."""
    import asyncio
    return asyncio.run(coro)


def cmd_analyze(symbol: str) -> None:
    """AI-powered comprehensive stock analysis."""
    _require_ai()
    from finscope.ai.config import get_ai_status
    status = get_ai_status()
    console.print(f"\n[dim]AI Provider: {status['provider']}[/dim]")
    console.print(f"Analyzing [bold cyan]{symbol}[/bold cyan]... (this may take 15-30 seconds)\n")

    from finscope.ai import analyze_stock
    analysis = _run_async(analyze_stock(symbol))

    # Render structured output
    console.print(Rule(f"AI Analysis: {symbol}", style="bold magenta"))
    console.print(f"\n[bold]Summary[/bold]")
    console.print(f"  {analysis.summary}\n")

    console.print(f"[bold green]Bull Case[/bold green]")
    for point in analysis.bull_case:
        console.print(f"  [green]+ {point}[/green]")

    console.print(f"\n[bold red]Bear Case[/bold red]")
    for point in analysis.bear_case:
        console.print(f"  [red]- {point}[/red]")

    console.print(f"\n[bold]Key Metrics[/bold]")
    console.print(f"  {analysis.key_metrics_commentary}\n")

    console.print(f"[bold]Financial Health[/bold]")
    console.print(f"  {analysis.financial_health}\n")

    console.print(f"[bold]Growth Outlook[/bold]")
    console.print(f"  {analysis.growth_outlook}\n")

    console.print(f"[bold yellow]Risk Factors[/bold yellow]")
    for risk in analysis.risk_factors:
        console.print(f"  [yellow]⚠ {risk}[/yellow]")

    sentiment_colors = {
        "Bullish": "bold green", "Moderately Bullish": "green",
        "Neutral": "yellow", "Moderately Bearish": "red",
        "Bearish": "bold red",
    }
    s_color = sentiment_colors.get(analysis.sentiment, "white")
    console.print(f"\n[bold]Sentiment:[/bold] [{s_color}]{analysis.sentiment}[/{s_color}]")
    console.print(f"[bold]Confidence:[/bold] {analysis.confidence}\n")


def cmd_ask(symbol: str, question: str) -> None:
    """Ask any question about a stock."""
    _require_ai()
    from finscope.ai.config import get_ai_status
    status = get_ai_status()
    console.print(f"\n[dim]AI Provider: {status['provider']}[/dim]")
    console.print(f"Thinking about [bold cyan]{symbol}[/bold cyan]...\n")

    from finscope.ai import ask_stock
    answer = _run_async(ask_stock(symbol, question))

    console.print(Rule(f"Q: {question}", style="cyan"))
    console.print(f"\n{answer}\n")


def cmd_ai_compare(symbols: list[str]) -> None:
    """AI-powered multi-stock comparison."""
    if len(symbols) < 2:
        console.print("[red]Please provide at least 2 tickers to compare.[/red]")
        return
    _require_ai()
    from finscope.ai.config import get_ai_status
    status = get_ai_status()
    console.print(f"\n[dim]AI Provider: {status['provider']}[/dim]")
    console.print(f"Comparing [bold cyan]{', '.join(symbols)}[/bold cyan]... (this may take 20-40 seconds)\n")

    from finscope.ai import ai_compare_stocks
    insight = _run_async(ai_compare_stocks(*symbols))

    console.print(Rule(f"AI Comparison: {', '.join(symbols)}", style="bold magenta"))
    console.print(f"\n[bold]Overview[/bold]")
    console.print(f"  {insight.overview}\n")

    console.print(f"[bold]Rankings[/bold]")
    for i, rank in enumerate(insight.rankings, 1):
        console.print(f"  {i}. {rank}")

    console.print(f"\n[bold]Valuation[/bold]")
    console.print(f"  {insight.valuation_comparison}\n")

    console.print(f"[bold]Growth[/bold]")
    console.print(f"  {insight.growth_comparison}\n")

    console.print(f"[bold]Risk[/bold]")
    console.print(f"  {insight.risk_comparison}\n")

    console.print(f"[bold]Best For[/bold]")
    for profile, rec in insight.best_for.items():
        console.print(f"  [cyan]{profile}:[/cyan] {rec}")
    console.print()


def cmd_summarize_filings(symbol: str) -> None:
    """AI-powered SEC filing summary."""
    _require_ai()
    from finscope.ai.config import get_ai_status
    status = get_ai_status()
    console.print(f"\n[dim]AI Provider: {status['provider']}[/dim]")
    console.print(f"Analyzing SEC filings for [bold cyan]{symbol}[/bold cyan]...\n")

    from finscope.ai import summarize_filings
    summary = _run_async(summarize_filings(symbol))

    console.print(Rule(f"SEC Filing Summary: {summary.company}", style="bold magenta"))
    console.print(f"\n[dim]Filings analyzed: {', '.join(summary.filing_types_covered)}[/dim]\n")

    console.print(f"[bold]Key Highlights[/bold]")
    for h in summary.key_highlights:
        console.print(f"  • {h}")

    console.print(f"\n[bold yellow]Risk Factors[/bold yellow]")
    for r in summary.risk_factors:
        console.print(f"  [yellow]⚠ {r}[/yellow]")

    console.print(f"\n[bold]Management Outlook[/bold]")
    console.print(f"  {summary.management_outlook}\n")

    if summary.notable_changes:
        console.print(f"[bold]Notable Changes[/bold]")
        for c in summary.notable_changes:
            console.print(f"  → {c}")
    console.print()


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
        render_attribution("Yahoo Finance")


class KeyRatiosCommand(DashboardCommand):
    def execute(self, ctx: DashboardContext) -> None:
        render_ratios(ctx.stock.ratios.to_display_dict())
        render_attribution("Yahoo Finance")


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
        render_attribution("Yahoo Finance")


class IncomeStatementCommand(DashboardCommand):
    def execute(self, ctx: DashboardContext) -> None:
        render_financials(ctx.stock.financials, "Income Statement")
        render_attribution("Yahoo Finance")


class BalanceSheetCommand(DashboardCommand):
    def execute(self, ctx: DashboardContext) -> None:
        render_financials(ctx.stock.balance_sheet, "Balance Sheet")
        render_attribution("Yahoo Finance")


class CashFlowCommand(DashboardCommand):
    def execute(self, ctx: DashboardContext) -> None:
        render_financials(ctx.stock.cashflow, "Cash Flow Statement")
        render_attribution("Yahoo Finance")


class NewsCommand(DashboardCommand):
    def execute(self, ctx: DashboardContext) -> None:
        render_news(ctx.stock.news)
        render_attribution("Yahoo Finance")


class AnalystRecsCommand(DashboardCommand):
    def execute(self, ctx: DashboardContext) -> None:
        render_analyst_recommendations(ctx.stock.analyst_recommendations)
        render_attribution("Yahoo Finance")


class MajorHoldersCommand(DashboardCommand):
    def execute(self, ctx: DashboardContext) -> None:
        breakdown, institutional = ctx.stock.holders
        render_major_holders(breakdown, institutional)
        render_attribution("Yahoo Finance")


class SecDetailedFinancialsCommand(DashboardCommand):
    def execute(self, ctx: DashboardContext) -> None:
        console.print("Loading detailed financials from SEC EDGAR...")
        edgar_data = ctx.stock.sec_financials
        if not edgar_data:
            console.print("[red]No SEC EDGAR data found for this ticker.[/red]")
            return
        sub = Prompt.ask("Category", choices=list(_SEC_CAT_MAP), default="income")
        render_detailed_financials(edgar_data, _SEC_CAT_MAP[sub])
        render_attribution("SEC EDGAR")


class SecFilingsCommand(DashboardCommand):
    def execute(self, ctx: DashboardContext) -> None:
        console.print("Loading recent SEC filings...")
        render_sec_filings(ctx.stock.sec_filings(count=20))
        render_attribution("SEC EDGAR")


class InsiderTransactionsCommand(DashboardCommand):
    def execute(self, ctx: DashboardContext) -> None:
        console.print("Loading insider transactions...")
        render_insider_transactions(ctx.stock.insider_transactions)
        render_attribution("SEC EDGAR")


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
        render_attribution("Yahoo Finance")


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
        render_attribution("Yahoo Finance")


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


def _show_menu(ctx: DashboardContext) -> DashboardCommand | None | ChangeTickerCommand:
    """Show the interactive menu using questionary (arrow keys + enter)."""
    console.print()
    
    choices = []
    for key, label in _REGISTRY.items():
        if key == 0:
            choices.append(questionary.Separator())
        choices.append(questionary.Choice(title=label, value=key))
        
    choice_key = questionary.select(
        "Select an option:",
        choices=choices,
        style=questionary.Style([
            ('qmark', 'fg:cyan bold'),
            ('question', 'bold'),
            ('answer', 'fg:green bold'),
            ('pointer', 'fg:cyan bold'),
            ('highlighted', 'fg:cyan bold'),
            ('selected', 'fg:green'),
            ('separator', 'fg:darkgray'),
        ]),
        instruction="(Use arrow keys to move, Enter to select)"
    ).ask()

    if choice_key is None or choice_key == 0:
        return None
        
    return _REGISTRY.get(choice_key)


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
        
        choices = []
        for key, label in _MF_MENU.items():
            if key == 0:
                choices.append(questionary.Separator())
            choices.append(questionary.Choice(title=label, value=key))
            
        choice = questionary.select(
            "Select Mutual Funds category:",
            choices=choices,
            style=questionary.Style([('pointer', 'fg:green bold'), ('highlighted', 'fg:green bold')]),
            instruction="(Use arrow keys to move, Enter to select)"
        ).ask()

        if choice is None or choice == 0:
            return

        if choice == 1:
            _india_fund_flow(fund_service)

        elif choice in _REGION_MAP:
            region = _REGION_MAP[choice]
            console.print(f"\nLoading {region} funds...")
            data = fund_service.get_popular_funds_snapshot(region)
            render_global_fund_snapshot(data, region)
            render_attribution("Yahoo Finance")

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
            render_attribution("Yahoo Finance")


def _india_fund_flow(fund_service: FundAnalysisService) -> None:
    while True:
        console.print()
        sub = questionary.select(
            "Indian Mutual Funds (MFAPI.in — 37,500+ funds):",
            choices=[
                questionary.Choice("Search by name", 1),
                questionary.Choice("Look up by scheme code", 2),
                questionary.Separator(),
                questionary.Choice("Back", 0),
            ],
            style=questionary.Style([('pointer', 'fg:cyan bold'), ('highlighted', 'fg:cyan bold')])
        ).ask()

        if sub is None or sub == 0:
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
        
    render_attribution("MFAPI.in")


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
        command = _show_menu(ctx)

        if command is None:
            console.print("[dim]Goodbye.[/dim]")
            sys.exit(0)

        if isinstance(command, ChangeTickerCommand):
            return True

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
  finscope AAPL valuate              Valuation analysis (6 models)
  finscope compare AAPL MSFT GOOGL  Side-by-side comparison
  finscope watchlist AAPL TSLA NVDA Compact watchlist
  finscope screen "pe < 15"         Screen S&P 500 stocks
  finscope export AAPL              HTML report
  finscope funds                    Mutual funds explorer
  finscope AAPL -i                  Interactive menu mode

AI-powered analysis (requires API key):
  finscope AAPL analyze               Comprehensive bull/bear analysis
  finscope AAPL ask "Is it overvalued?"  Ask anything about a stock
  finscope compare AAPL MSFT --analyze   AI comparison insight
  finscope AAPL summarize-filings     SEC filing summary
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
    parser.add_argument(
        "--analyze",
        action="store_true",
        help="Use AI analysis (for compare command)",
    )
    return parser


def _dispatch(parsed: argparse.Namespace) -> None:
    """Route parsed CLI args to the right command function."""
    args: list[str] = parsed.args
    interactive: bool = parsed.interactive

    # ── No arguments at all → interactive prompt ──────────────────────────
    if not args:
        _print_banner()
        while True:
            symbol = Prompt.ask("Enter a stock ticker (e.g., AAPL, TSLA, MSFT, or 'exit' to quit)")
            if symbol.strip().lower() in ('exit', 'quit', 'q'):
                console.print("[dim]Goodbye.[/dim]")
                break
            if not symbol.strip():
                continue
            change = run_interactive(symbol.strip().upper())
            if not change:
                break
        return

    first = args[0].lower()

    # ── Top-level keyword commands ────────────────────────────────────────
    if first == "compare":
        symbols = [s.upper() for s in args[1:]]
        if parsed.analyze:
            cmd_ai_compare(symbols)
        else:
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

    if first == "screen":
        if len(args) < 2:
            console.print("[red]Usage: finscope screen \"QUERY\"[/red]")
            console.print("[dim]Example: finscope screen \"pe < 20 and roe > 15\"[/dim]")
            return
        cmd_screen(" ".join(args[1:]))
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
            symbol = Prompt.ask("Enter a stock ticker (or 'exit' to quit)").strip().upper()
            if symbol.lower() in ('exit', 'quit', 'q'):
                break
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
        "insiders":          lambda: cmd_insiders(symbol),
        "valuate":           lambda: cmd_valuate(symbol),
        "analyze":           lambda: cmd_analyze(symbol),
        "ask":               lambda: cmd_ask(symbol, " ".join(args[2:]) if len(args) > 2 else ""),
        "summarize-filings": lambda: cmd_summarize_filings(symbol),
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
