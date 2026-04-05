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
    "valuate", "risk",
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
    console.print(Rule("Graham Number  [dim](src: Yahoo Finance — EPS, Book Value)[/dim]", style="cyan"))
    console.print("  [dim]What it means: Stocks trading [bold]below[/bold] their Graham Number have a margin of safety. "
                  "Formula: \u221a(22.5 \u00d7 EPS \u00d7 Book Value) \u2014 assumes max 15\u00d7 earnings and 1.5\u00d7 book value. "
                  "Best for mature, asset-heavy companies. Most high-growth tech stocks fail this test because "
                  "their value lies in intangibles, not book value.[/dim]")
    g = v.graham
    if g.calculable:
        console.print(f"  EPS: {g.eps:.2f}  |  Book Value: {g.book_value_per_share:.2f}")
        console.print(f"  Intrinsic Value: [bold]${g.intrinsic:.2f}[/bold]")
        ms_c = "green" if g.margin_of_safety_pct and g.margin_of_safety_pct > 0 else "red"
        console.print(f"  Margin of Safety: [{ms_c}]{g.margin_of_safety_pct:+.1f}%[/{ms_c}]  → {g.signal}")
    else:
        console.print("  [dim]Cannot compute (negative EPS or book value)[/dim]")

    # DCF
    console.print(Rule("DCF (Discounted Cash Flow)  [dim](src: Yahoo Finance — Free Cash Flow, Beta, Growth)[/dim]", style="cyan"))
    console.print("  [dim]What it means: Projects future free cash flows and discounts them to today's value. "
                  "The most comprehensive intrinsic value model, but highly sensitive to inputs \u2014 "
                  "a 2% change in growth rate can swing the result by 30\u201350%. "
                  "Discount rate is estimated via CAPM (risk-free rate + beta \u00d7 market premium). "
                  "Most reliable for companies with stable, predictable cash flows.[/dim]")
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
    console.print(Rule("PEG Fair Value (Peter Lynch)  [dim](src: Yahoo Finance — EPS, Earnings Growth)[/dim]", style="cyan"))
    console.print("  [dim]What it means: Peter Lynch's rule \u2014 a fairly valued stock has P/E equal to its "
                  "earnings growth rate (PEG = 1). Fair price = growth rate \u00d7 EPS. "
                  "PEG < 1: potentially undervalued relative to growth. PEG > 1.5: potentially overvalued. "
                  "Unreliable when earnings are negative or highly volatile.[/dim]")
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
    console.print(Rule("Relative Valuation  [dim](src: Yahoo Finance — P/E, P/B, 50D/200D Averages)[/dim]", style="cyan"))
    console.print("  [dim]What it means: Compares the current price to the stock's own moving averages and multiples. "
                  "This is relative (not absolute) \u2014 trading below the 200D avg means historically cheap "
                  "for [bold]this stock[/bold], not necessarily cheap in absolute terms. "
                  "P/E < 12 is broadly cheap; P/E > 35 is expensive.[/dim]")
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
    console.print(Rule("Piotroski F-Score  [dim](src: Yahoo Finance — ROA, OCF, Margins, Ratios)[/dim]", style="cyan"))
    console.print("  [dim]What it means: A 9-point [bold]financial health[/bold] checklist, not a price model. "
                  "4 pts for profitability, 3 for leverage/liquidity, 2 for efficiency. "
                  "8\u20139 = financially strong (bullish signal), 5\u20137 = average, 0\u20134 = weak (bearish signal). "
                  "A high score means strong fundamentals \u2014 a company can still be expensive with a high score.[/dim]")
    f = v.piotroski
    bar = "\u2588" * f.score + "\u2591" * (9 - f.score)
    score_color = "green" if f.score >= 7 else "yellow" if f.score >= 4 else "red"
    console.print(f"  Score: [{score_color}]{bar} {f.score}/9 ({f.strength})[/{score_color}]")
    for criterion, passed in f.details.items():
        icon = "[green]\u2713[/green]" if passed else "[red]\u2717[/red]"
        console.print(f"    {icon} {criterion}")

    # Altman Z-Score
    console.print(Rule("Altman Z-Score  [dim](src: Yahoo Finance — Assets, Liabilities, EBITDA, Revenue)[/dim]", style="cyan"))
    console.print("  [dim]What it means: A [bold]bankruptcy risk[/bold] indicator, not a valuation model. "
                  "Z > 2.99 = Safe (low distress risk). 1.81\u20132.99 = Grey zone (monitor closely). "
                  "Z < 1.81 = Distress zone (elevated bankruptcy risk). "
                  "Originally designed for manufacturing companies \u2014 less reliable for asset-light tech or financial firms.[/dim]")
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

    render_attribution("Yahoo Finance (fundamentals) · SEC EDGAR (balance sheet)")
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
    render_attribution("Yahoo Finance")


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


def cmd_risk(symbol: str, period: str = "1y") -> None:
    """Full risk profile: volatility, drawdown, Sharpe, beta, fundamentals."""
    console.print(f"\nComputing risk profile for [bold cyan]{symbol}[/bold cyan] ({period})...\n")
    from finscope.risk import compute_risk
    r = compute_risk(symbol, period=period)

    # ── Composite ──────────────────────────────────────────────────────────
    level_colors = {
        "Low": "bold green", "Moderate": "yellow",
        "High": "bold red", "Very High": "bold red on white",
    }
    lc = level_colors.get(r.risk_level, "white")
    bar_len = int((r.risk_score or 0) / 5)
    bar = "█" * bar_len + "░" * (20 - bar_len)

    console.print(Rule(f"Risk Profile: {r.symbol}", style="bold magenta"))
    console.print(f"  [{lc}]{bar} {r.risk_score:.0f}/100  {r.risk_level} Risk[/{lc}]\n")

    if r.risk_factors:
        console.print("[bold red]  ⚠ Risk Factors[/bold red]")
        for f_ in r.risk_factors:
            console.print(f"    [red]• {f_}[/red]")
    if r.risk_positives:
        console.print("\n[bold green]  ✓ Mitigating Factors[/bold green]")
        for p in r.risk_positives:
            console.print(f"    [green]• {p}[/green]")
    console.print()

    # ── Volatility ─────────────────────────────────────────────────────────
    console.print(Rule("Volatility  [dim](src: price history — daily returns)[/dim]", style="cyan"))
    console.print("  [dim]What it means: How much the stock price fluctuates. "
                  "Annual volatility < 15% = low risk. 15–25% = moderate. "
                  "25–40% = high. > 40% = very high. "
                  "Skewness < 0 = left tail (risk of sudden drops). "
                  "High kurtosis = fat tails (extreme moves more likely than normal distribution predicts).[/dim]")
    v = r.volatility
    if v.annual_vol is not None:
        vc = "green" if v.annual_vol < 0.20 else "yellow" if v.annual_vol < 0.35 else "red"
        console.print(f"  Annual Volatility:   [{vc}]{v.annual_vol:.1%}[/{vc}]  ({v.interpretation})")
        console.print(f"  Daily Volatility:    {v.daily_vol:.2%}" if v.daily_vol else "")
        console.print(f"  30D Volatility:      {v.vol_30d:.1%}" if v.vol_30d else "")
        console.print(f"  90D Volatility:      {v.vol_90d:.1%}" if v.vol_90d else "")
        if v.skewness is not None:
            sk_c = "red" if v.skewness < -0.5 else "green" if v.skewness > 0.5 else "dim"
            console.print(f"  Skewness:            [{sk_c}]{v.skewness:.2f}[/{sk_c}]"
                          f"  [dim]({'negative tail risk' if v.skewness < 0 else 'positive skew'})[/dim]")
        if v.kurtosis is not None:
            kc = "red" if v.kurtosis > 3 else "dim"
            console.print(f"  Kurtosis:            [{kc}]{v.kurtosis:.2f}[/{kc}]"
                          f"  [dim]({'fat tails — extreme moves likely' if v.kurtosis > 3 else 'normal tails'})[/dim]")
    else:
        console.print("  [dim]Insufficient price data[/dim]")

    # ── Downside Risk ──────────────────────────────────────────────────────
    console.print(Rule("Downside Risk  [dim](src: price history — worst-case scenarios)[/dim]", style="cyan"))
    console.print("  [dim]What it means: VaR 95% = the loss you won't exceed on 95% of trading days. "
                  "CVaR = average loss on the worst 5% of days (expected shortfall). "
                  "Max drawdown = the largest peak-to-trough decline ever recorded in the period. "
                  "Current drawdown = how far the stock is from its 52-week high right now.[/dim]")
    d = r.downside
    if d.var_95 is not None:
        vc = "red" if d.var_95 < -0.03 else "yellow"
        console.print(f"  VaR 95%:             [{vc}]{d.var_95:.2%}[/{vc}]  [dim](daily loss not exceeded 95% of days)[/dim]")
    if d.var_99 is not None:
        console.print(f"  VaR 99%:             [red]{d.var_99:.2%}[/red]  [dim](daily loss not exceeded 99% of days)[/dim]")
    if d.cvar_95 is not None:
        console.print(f"  CVaR 95%:            [red]{d.cvar_95:.2%}[/red]  [dim](avg loss on worst 5% of days)[/dim]")
    if d.max_drawdown is not None:
        mdc = "green" if d.max_drawdown > -0.15 else "yellow" if d.max_drawdown > -0.30 else "red"
        console.print(f"  Max Drawdown:        [{mdc}]{d.max_drawdown:.1%}[/{mdc}]", end="")
        if d.drawdown_start and d.drawdown_end:
            console.print(f"  [dim]({d.drawdown_start} → {d.drawdown_end})[/dim]", end="")
        console.print()
        if d.max_drawdown_duration:
            console.print(f"  Recovery Duration:   {d.max_drawdown_duration} days")
    if d.current_drawdown is not None:
        cdc = "green" if d.current_drawdown > -0.10 else "yellow" if d.current_drawdown > -0.25 else "red"
        console.print(f"  vs 52W High:         [{cdc}]{d.current_drawdown:.1%}[/{cdc}]  [dim](current drawdown)[/dim]")

    # ── Risk-Adjusted Returns ──────────────────────────────────────────────
    console.print(Rule("Risk-Adjusted Returns  [dim](src: price history vs risk-free rate 4%)[/dim]", style="cyan"))
    console.print("  [dim]What it means: Sharpe ratio = excess return per unit of total volatility "
                  "(> 1.0 is good, > 2.0 is excellent, < 0 means you weren't compensated for risk). "
                  "Sortino only penalises downside volatility — better for asymmetric returns. "
                  "Calmar = annual return ÷ max drawdown (higher is better).[/dim]")
    ra = r.risk_adjusted
    if ra.annual_return is not None:
        arc = "green" if ra.annual_return > 0 else "red"
        console.print(f"  Annual Return:       [{arc}]{ra.annual_return:+.1%}[/{arc}]  [dim](over {r.period} period)[/dim]")
    if ra.sharpe_ratio is not None:
        sc = "green" if ra.sharpe_ratio > 1 else "yellow" if ra.sharpe_ratio > 0 else "red"
        console.print(f"  Sharpe Ratio:        [{sc}]{ra.sharpe_ratio:.2f}[/{sc}]  [dim]({ra.interpretation})[/dim]")
    if ra.sortino_ratio is not None:
        sc = "green" if ra.sortino_ratio > 1 else "yellow" if ra.sortino_ratio > 0 else "red"
        console.print(f"  Sortino Ratio:       [{sc}]{ra.sortino_ratio:.2f}[/{sc}]")
    if ra.calmar_ratio is not None:
        cc = "green" if ra.calmar_ratio > 1 else "yellow" if ra.calmar_ratio > 0 else "red"
        console.print(f"  Calmar Ratio:        [{cc}]{ra.calmar_ratio:.2f}[/{cc}]")

    # ── Market Risk ────────────────────────────────────────────────────────
    console.print(Rule("Market Risk  [dim](src: price history vs SPY)[/dim]", style="cyan"))
    console.print("  [dim]What it means: Beta measures sensitivity to the S&P 500. "
                  "Beta = 1.0 moves in line with the market. "
                  "Beta > 1.5 amplifies market moves (higher risk and reward). "
                  "Beta < 0.6 is defensive. Beta < 0 moves inversely. "
                  "R-squared tells you how much of this stock's movement is explained by the market.[/dim]")
    m = r.market
    beta = m.beta or m.beta_calculated
    if beta is not None:
        bc = "green" if beta < 0.8 else "yellow" if beta < 1.3 else "red"
        console.print(f"  Beta:                [{bc}]{beta:.2f}[/{bc}]  [dim]({m.interpretation})[/dim]")
        if m.beta and m.beta_calculated:
            console.print(f"  Beta (calculated):   {m.beta_calculated:.2f}  [dim](vs {m.beta:.2f} from data provider)[/dim]")
    if m.correlation is not None:
        console.print(f"  Correlation (SPY):   {m.correlation:.2f}")
    if m.r_squared is not None:
        console.print(f"  R-Squared (SPY):     {m.r_squared:.1%}  [dim](% of movement explained by market)[/dim]")

    # ── Fundamental Risk ───────────────────────────────────────────────────
    console.print(Rule("Fundamental Risk  [dim](src: Yahoo Finance — balance sheet)[/dim]", style="cyan"))
    console.print("  [dim]What it means: Balance sheet health. "
                  "Debt/Equity > 200% is high leverage. "
                  "Current ratio < 1.0 means more short-term liabilities than assets. "
                  "Interest coverage < 2× means earnings barely cover interest payments. "
                  "Earnings quality: good when operating cash flow exceeds reported net income.[/dim]")
    fu = r.fundamental
    if fu.debt_to_equity is not None:
        dc = "green" if fu.debt_to_equity < 80 else "yellow" if fu.debt_to_equity < 150 else "red"
        console.print(f"  Debt / Equity:       [{dc}]{fu.debt_to_equity:.0f}%[/{dc}]")
    if fu.current_ratio is not None:
        crc = "green" if fu.current_ratio > 1.5 else "yellow" if fu.current_ratio > 1.0 else "red"
        console.print(f"  Current Ratio:       [{crc}]{fu.current_ratio:.2f}[/{crc}]")
    if fu.interest_coverage is not None:
        icc = "green" if fu.interest_coverage > 5 else "yellow" if fu.interest_coverage > 2 else "red"
        console.print(f"  Interest Coverage:   [{icc}]{fu.interest_coverage:.1f}×[/{icc}]")
    if fu.altman_z is not None:
        zc = {"Safe": "green", "Grey": "yellow", "Distress": "bold red"}.get(fu.altman_zone, "white")
        console.print(f"  Altman Z-Score:      [{zc}]{fu.altman_z:.2f} ({fu.altman_zone})[/{zc}]")
    if fu.earnings_quality != "N/A":
        eqc = "green" if fu.earnings_quality == "Good" else "red"
        console.print(f"  Earnings Quality:    [{eqc}]{fu.earnings_quality}[/{eqc}]  [dim](OCF vs Net Income)[/dim]")

    render_attribution(f"Yahoo Finance · price history ({r.period})")
    console.print()


# ── Fund risk & analysis renderers ───────────────────────────────────────────


def _render_fund_risk(r: "FundRisk") -> None:
    """Render a FundRisk result to the terminal."""
    from finscope.fund_analysis.models import FundRisk
    level_colors = {"Low": "bold green", "Moderate": "yellow",
                    "High": "bold red", "Very High": "bold red on white"}
    lc  = level_colors.get(r.risk_level, "white")
    bar = "█" * int((r.risk_score or 0) / 5) + "░" * (20 - int((r.risk_score or 0) / 5))

    console.print(Rule(f"Fund Risk: {r.name}", style="bold magenta"))
    console.print(f"  [{lc}]{bar} {r.risk_score:.0f}/100  {r.risk_level} Risk[/{lc}]\n")

    if r.risk_factors:
        console.print("[bold red]  ⚠ Risk Factors[/bold red]")
        for f_ in r.risk_factors:
            console.print(f"    [red]• {f_}[/red]")
    if r.risk_positives:
        console.print("\n[bold green]  ✓ Mitigating Factors[/bold green]")
        for p in r.risk_positives:
            console.print(f"    [green]• {p}[/green]")
    console.print()

    # Volatility
    console.print(Rule("Volatility  [dim](src: price/NAV history)[/dim]", style="cyan"))
    console.print("  [dim]How much the NAV/price fluctuates. Annual < 15% = low. 15–25% = moderate. > 40% = very high.[/dim]")
    v = r.volatility
    if v.annual_vol is not None:
        vc = "green" if v.annual_vol < 0.20 else "yellow" if v.annual_vol < 0.35 else "red"
        console.print(f"  Annual Volatility: [{vc}]{v.annual_vol:.1%}[/{vc}]  ({v.interpretation})")
        if v.vol_30d:  console.print(f"  30D Volatility:    {v.vol_30d:.1%}")
        if v.vol_90d:  console.print(f"  90D Volatility:    {v.vol_90d:.1%}")
        if v.skewness is not None:
            sc = "red" if v.skewness < -0.5 else "green" if v.skewness > 0.5 else "dim"
            console.print(f"  Skewness:          [{sc}]{v.skewness:.2f}[/{sc}]  [dim]({'left tail risk' if v.skewness < 0 else 'positive skew'})[/dim]")
        if v.kurtosis is not None:
            kc = "red" if v.kurtosis > 3 else "dim"
            console.print(f"  Kurtosis:          [{kc}]{v.kurtosis:.2f}[/{kc}]  [dim]({'fat tails' if v.kurtosis > 3 else 'normal tails'})[/dim]")

    # Downside
    console.print(Rule("Downside Risk", style="cyan"))
    console.print("  [dim]VaR 95% = daily loss not exceeded on 95% of days. "
                  "CVaR = average loss on worst 5% of days. "
                  "Max drawdown = largest peak-to-trough decline.[/dim]")
    d = r.downside
    if d.var_95 is not None:
        vc = "red" if d.var_95 < -0.03 else "yellow"
        console.print(f"  VaR 95%:           [{vc}]{d.var_95:.2%}[/{vc}]")
    if d.var_99 is not None:
        console.print(f"  VaR 99%:           [red]{d.var_99:.2%}[/red]")
    if d.cvar_95 is not None:
        console.print(f"  CVaR 95%:          [red]{d.cvar_95:.2%}[/red]")
    if d.max_drawdown is not None:
        mdc = "green" if d.max_drawdown > -0.15 else "yellow" if d.max_drawdown > -0.30 else "red"
        console.print(f"  Max Drawdown:      [{mdc}]{d.max_drawdown:.1%}[/{mdc}]", end="")
        if d.drawdown_start and d.drawdown_end:
            console.print(f"  [dim]({d.drawdown_start} → {d.drawdown_end})[/dim]", end="")
        console.print()
        if d.max_drawdown_duration:
            console.print(f"  Recovery:          {d.max_drawdown_duration} days")
    if d.current_drawdown is not None:
        cdc = "green" if d.current_drawdown > -0.10 else "yellow" if d.current_drawdown > -0.25 else "red"
        console.print(f"  Current Drawdown:  [{cdc}]{d.current_drawdown:.1%}[/{cdc}]  [dim](from 52W high)[/dim]")

    # Risk-adjusted
    console.print(Rule("Risk-Adjusted Returns  [dim](risk-free rate 4%)[/dim]", style="cyan"))
    console.print("  [dim]Sharpe > 1.0 = good. Sortino only penalises downside. Calmar = return ÷ drawdown.[/dim]")
    ra = r.risk_adjusted
    if ra.annual_return is not None:
        arc = "green" if ra.annual_return > 0 else "red"
        console.print(f"  Annual Return:     [{arc}]{ra.annual_return:+.1%}[/{arc}]  [dim](over {r.period} period)[/dim]")
    if ra.sharpe_ratio is not None:
        sc = "green" if ra.sharpe_ratio > 1 else "yellow" if ra.sharpe_ratio > 0 else "red"
        console.print(f"  Sharpe Ratio:      [{sc}]{ra.sharpe_ratio:.2f}[/{sc}]  [dim]({ra.interpretation})[/dim]")
    if ra.sortino_ratio is not None:
        sc = "green" if ra.sortino_ratio > 1 else "yellow" if ra.sortino_ratio > 0 else "red"
        console.print(f"  Sortino Ratio:     [{sc}]{ra.sortino_ratio:.2f}[/{sc}]")
    if ra.calmar_ratio is not None:
        cc = "green" if ra.calmar_ratio > 1 else "yellow" if ra.calmar_ratio > 0 else "red"
        console.print(f"  Calmar Ratio:      [{cc}]{ra.calmar_ratio:.2f}[/{cc}]")

    # Beta (global ETFs only)
    if r.beta is not None or r.correlation_vs_market is not None:
        console.print(Rule("Market Sensitivity  [dim](vs SPY)[/dim]", style="cyan"))
        console.print("  [dim]Beta < 0.8 = defensive. Beta > 1.2 = amplifies market moves.[/dim]")
        if r.beta is not None:
            bc = "green" if r.beta < 0.8 else "yellow" if r.beta < 1.3 else "red"
            console.print(f"  Beta:              [{bc}]{r.beta:.2f}[/{bc}]")
        if r.correlation_vs_market is not None:
            console.print(f"  Correlation (SPY): {r.correlation_vs_market:.2f}")
        if r.r_squared is not None:
            console.print(f"  R-Squared (SPY):   {r.r_squared:.1%}")


def _render_fund_analysis(a: "FundAnalysis") -> None:
    """Render a FundAnalysis result to the terminal."""
    rating_colors = {"Strong": "bold green", "Good": "green",
                     "Average": "yellow", "Below Average": "red", "Weak": "bold red"}
    rc = rating_colors.get(a.overall_rating, "white")

    console.print(Rule(f"Fund Analysis: {a.name}", style="bold magenta"))
    console.print(f"  Overall Rating: [{rc}]{a.overall_rating}[/{rc}]")
    console.print(f"  Category:       {a.category}")
    console.print(f"  Fund House:     {a.fund_house}\n")

    if a.highlights:
        console.print("[bold green]  ✓ Highlights[/bold green]")
        for h in a.highlights:
            console.print(f"    [green]• {h}[/green]")
    if a.concerns:
        console.print("[bold red]  ⚠ Concerns[/bold red]")
        for c in a.concerns:
            console.print(f"    [red]• {c}[/red]")
    console.print()

    # Cost
    console.print(Rule("Cost Efficiency  [dim](expense ratio)[/dim]", style="cyan"))
    console.print("  [dim]Expense ratio = annual fee as % of AUM. ETFs < 0.10% = excellent. "
                  "Active funds < 0.50% = good. Higher fees directly reduce your returns.[/dim]")
    if a.expense_ratio is not None:
        er_color = "green" if a.expense_rating in ("Excellent", "Good") else "yellow" if a.expense_rating == "Average" else "red"
        console.print(f"  Expense Ratio: [{er_color}]{a.expense_ratio:.3%}[/{er_color}]  ({a.expense_rating})")
    else:
        console.print("  [dim]Expense ratio not available[/dim]")
    if a.aum is not None:
        console.print(f"  AUM:           ${a.aum/1e9:.2f}B  ({a.aum_rating})" if a.aum >= 1e9
                      else f"  AUM:           ${a.aum/1e6:.0f}M  ({a.aum_rating})")

    # Rolling returns
    console.print(Rule("Rolling Returns (CAGR)  [dim](src: price/NAV history)[/dim]", style="cyan"))
    console.print("  [dim]CAGR = Compound Annual Growth Rate. Shows what ₹100 invested would be worth "
                  "annualised over each period. Compare against category/benchmark.[/dim]")
    from finscope.ui.builders import TableBuilder
    builder = (
        TableBuilder("")
        .border("green")
        .column("Period", style="bold", min_width=8)
    )
    labels = [k for k in ["1M", "3M", "6M", "1Y", "3Y", "5Y"] if k in a.rolling_returns]
    for label in labels:
        builder.column(label, justify="right", min_width=10)
    row = []
    for label in labels:
        val = a.rolling_returns.get(label)
        if val is None:
            row.append("[dim]N/A[/dim]")
        else:
            color = "green" if val > 0 else "red"
            row.append(f"[{color}]{val:+.1%}[/{color}]")
    if row:
        builder.row("Return", *row)
        console.print(builder.build())

    # Consistency
    if a.consistency_score is not None:
        console.print(Rule("Consistency", style="cyan"))
        console.print("  [dim]% of rolling 12-month windows with a positive return. "
                      "> 80% = very consistent. < 50% = unreliable.[/dim]")
        cc = "green" if a.consistency_score > 0.80 else "yellow" if a.consistency_score > 0.60 else "red"
        console.print(f"  Rolling 1Y Consistency: [{cc}]{a.consistency_score:.0%}[/{cc}] of windows positive")


def cmd_global_fund_risk(symbol: str, period: str = "1y") -> None:
    """Risk profile for a global ETF or mutual fund."""
    console.print(f"\nComputing risk for [bold cyan]{symbol}[/bold cyan] ({period})...\n")
    from finscope.fund_analysis import analyze_global_fund
    import finscope
    fund = finscope.fund(symbol)
    r, _ = analyze_global_fund(symbol, fund=fund, period=period)
    _render_fund_risk(r)
    render_attribution(f"Yahoo Finance · price history ({period})")


def cmd_global_fund_analyze(symbol: str) -> None:
    """Fund-specific analysis for a global ETF or mutual fund."""
    console.print(f"\nAnalysing fund [bold cyan]{symbol}[/bold cyan]...\n")
    from finscope.fund_analysis import analyze_global_fund
    import finscope
    fund = finscope.fund(symbol)
    _, a = analyze_global_fund(symbol, fund=fund)
    _render_fund_analysis(a)
    render_attribution("Yahoo Finance")


def cmd_india_fund_risk_and_analysis(fund_service: "FundAnalysisService",
                                      scheme_code: str) -> None:
    """Risk + analysis for an Indian mutual fund (MFAPI)."""
    console.print(f"\nLoading scheme {scheme_code}...\n")
    detail = fund_service.get_india_fund_detail(scheme_code)
    if not detail:
        console.print(f"[red]Could not fetch fund {scheme_code}.[/red]")
        return
    meta     = detail.get("meta", {})
    nav_data = detail.get("data", [])

    from finscope.fund_analysis import analyze_india_fund
    r, a = analyze_india_fund(nav_data, meta)
    _render_fund_risk(r)
    console.print()
    _render_fund_analysis(a)
    render_attribution("MFAPI.in")
    # Offer deeper analysis
    deeper = questionary.select(
        "Deep dive:",
        choices=[
            questionary.Choice("Risk Profile (volatility, VaR, drawdown, Sharpe)", "risk"),
            questionary.Choice("Fund Analysis (rolling returns, consistency)", "analyze"),
            questionary.Choice("Skip", "skip"),
        ],
        style=questionary.Style([("pointer", "fg:cyan bold"), ("highlighted", "fg:cyan bold")]),
    ).ask()
    if deeper in ("risk", "analyze"):
        cmd_india_fund_risk_and_analysis(fund_service, scheme_code)


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
    render_attribution(f"Yahoo Finance · SEC EDGAR · {status['provider']} (AI)")


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
    render_attribution(f"Yahoo Finance · {status['provider']} (AI)")


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
    render_attribution(f"Yahoo Finance · {status['provider']} (AI)")


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
    render_attribution(f"SEC EDGAR · {status['provider']} (AI)")


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


class ValuateCommand(DashboardCommand):
    def execute(self, ctx: DashboardContext) -> None:
        cmd_valuate(ctx.symbol)



class RiskCommand(DashboardCommand):
    def execute(self, ctx: DashboardContext) -> None:
        period = questionary.select(
            "Look-back period:",
            choices=[
                questionary.Choice("6 months", "6mo"),
                questionary.Choice("1 year (default)", "1y"),
                questionary.Choice("2 years", "2y"),
                questionary.Choice("5 years", "5y"),
            ],
            default="1y",
        ).ask() or "1y"
        cmd_risk(ctx.symbol, period)


class ScreenCommand(DashboardCommand):
    def execute(self, ctx: DashboardContext) -> None:
        query = Prompt.ask(
            "Screener query",
            default="pe < 20 and roe > 15",
        )
        cmd_screen(query)


class AIAnalysisCommand(DashboardCommand):
    """Opens the AI analysis submenu (requires an LLM API key)."""

    def execute(self, ctx: DashboardContext) -> None:
        from finscope.ai.config import is_ai_available, get_ai_status

        if not is_ai_available():
            console.print(
                "\n[red bold]\u2717 AI features require an LLM provider API key.[/red bold]\n"
                "[dim]Set one of: OPENAI_API_KEY, ANTHROPIC_API_KEY, "
                "GEMINI_API_KEY, GROQ_API_KEY, MISTRAL_API_KEY[/dim]\n"
            )
            return

        status = get_ai_status()
        console.print(f"\n[dim]AI Provider: {status['provider']}[/dim]\n")

        choice = questionary.select(
            "AI Analysis:",
            choices=[
                questionary.Choice("\U0001f9e0  Comprehensive stock analysis",       "analyze"),
                questionary.Choice("\U0001f4ac  Ask a question about this stock",    "ask"),
                questionary.Choice("\U0001f4c4  Summarize SEC filings",              "summarize"),
                questionary.Choice("\U0001f4ca  AI comparison with other stocks",    "compare"),
                questionary.Separator(),
                questionary.Choice("\u2190  Back",                                   "back"),
            ],
            style=questionary.Style([
                ("pointer",     "fg:magenta bold"),
                ("highlighted", "fg:magenta bold"),
            ]),
            instruction="(Use arrow keys, Enter to select)",
        ).ask()

        if not choice or choice == "back":
            return

        if choice == "analyze":
            cmd_analyze(ctx.symbol)

        elif choice == "ask":
            question = Prompt.ask("Your question")
            if question.strip():
                cmd_ask(ctx.symbol, question.strip())

        elif choice == "summarize":
            cmd_summarize_filings(ctx.symbol)

        elif choice == "compare":
            raw = Prompt.ask(
                "Additional tickers to compare against (comma-separated)",
                default="MSFT,GOOGL",
            )
            others = [t.strip().upper() for t in raw.split(",") if t.strip()]
            cmd_ai_compare([ctx.symbol] + others)


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
        render_attribution("Yahoo Finance")


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


def _print_session_header(stock: Stock) -> None:
    """Print a prominent session header once a ticker is loaded."""
    info = stock.info
    name     = info.get("longName") or info.get("shortName", stock.symbol)
    symbol   = info.get("symbol", stock.symbol).upper()
    price    = info.get("currentPrice") or info.get("regularMarketPrice", "N/A")
    change   = info.get("regularMarketChangePercent", 0)
    currency = info.get("currency", "USD")
    sector   = info.get("sector", "")
    industry = info.get("industry", "")
    exchange = info.get("exchange", "")

    price_color = "green" if isinstance(change, (int, float)) and change >= 0 else "red"
    change_str  = f"[{price_color}]{change:+.2f}%[/{price_color}]" if isinstance(change, (int, float)) else ""

    console.print()
    console.print(Rule(style="blue"))
    console.print(
        f"  [bold white]{name}[/bold white]  "
        f"[bold cyan]({symbol})[/bold cyan]  "
        f"[dim]{exchange}[/dim]"
    )
    if sector:
        console.print(f"  [dim italic]{sector}{' / ' + industry if industry else ''}[/dim italic]")
    console.print(
        f"  [{price_color}][bold]{currency} {price}[/bold][/{price_color}]  {change_str}"
    )
    console.print(Rule(style="blue"))
    console.print()


def _build_registry() -> CommandRegistry:
    return (
        CommandRegistry()
        # ── Overview ───────────────────────────────────────────────────────
        .register(1,  "Company Overview",                      OverviewCommand())
        .register(2,  "Key Ratios",                            KeyRatiosCommand())
        .register(3,  "Price History (with sparkline)",        PriceHistoryCommand())
        # ── Financials ─────────────────────────────────────────────────────
        .register(4,  "Income Statement",                      IncomeStatementCommand())
        .register(5,  "Balance Sheet",                         BalanceSheetCommand())
        .register(6,  "Cash Flow Statement",                   CashFlowCommand())
        # ── Market data ────────────────────────────────────────────────────
        .register(7,  "News",                                  NewsCommand())
        .register(8,  "Analyst Recommendations",               AnalystRecsCommand())
        .register(9,  "Major Holders",                         MajorHoldersCommand())
        # ── SEC EDGAR ──────────────────────────────────────────────────────
        .register(10, "SEC EDGAR: Detailed Financials (XBRL)", SecDetailedFinancialsCommand())
        .register(11, "SEC EDGAR: Recent Filings",             SecFilingsCommand())
        .register(12, "SEC EDGAR: Insider Transactions",       InsiderTransactionsCommand())
        # ── Valuation & Screening ──────────────────────────────────────────
        .register(13, "Valuation Analysis (6 models)",         ValuateCommand())
        .register(14, "Risk Profile (volatility, VaR, Sharpe)",  RiskCommand())
        .register(15, "Stock Screener (S&P 500)",              ScreenCommand())
        # ── Comparison & Watchlist ─────────────────────────────────────────
        .register(16, "Compare Stocks",                        CompareStocksCommand())
        .register(17, "Watchlist",                             WatchlistCommand())
        # ── AI ─────────────────────────────────────────────────────────────
        .register(17, "\U0001f9e0  AI Analysis →",              AIAnalysisCommand())
        # ── Utilities ──────────────────────────────────────────────────────
        .register(19, "Export Report to HTML",                 ExportHtmlCommand())
        .register(20, "Mutual Funds",                          MutualFundsCommand())
        .register(20, "Change Ticker",                         ChangeTickerCommand())
        .register(0,  "Exit",                                  None)
    )


_REGISTRY = _build_registry()


def _show_menu(ctx: DashboardContext) -> DashboardCommand | None | ChangeTickerCommand:
    """Show the interactive menu using questionary (arrow keys + enter)."""
    console.print()

    # Build choices with group separators
    choices: list = [
        questionary.Separator("─── Overview ───────────────────────────────"),
        questionary.Choice("Company Overview",             1),
        questionary.Choice("Key Ratios",                   2),
        questionary.Choice("Price History (with sparkline)",3),
        questionary.Separator("─── Financials ─────────────────────────────"),
        questionary.Choice("Income Statement",             4),
        questionary.Choice("Balance Sheet",                5),
        questionary.Choice("Cash Flow Statement",          6),
        questionary.Separator("─── Market Data ────────────────────────────"),
        questionary.Choice("News",                         7),
        questionary.Choice("Analyst Recommendations",      8),
        questionary.Choice("Major Holders",                9),
        questionary.Separator("─── SEC EDGAR ──────────────────────────────"),
        questionary.Choice("Detailed Financials (XBRL)",   10),
        questionary.Choice("Recent Filings",               11),
        questionary.Choice("Insider Transactions",         12),
        questionary.Separator("─── Valuation & Screening ──────────────────"),
        questionary.Choice("Valuation Analysis (6 models)",13),
        questionary.Choice("Risk Profile (vol, VaR, Sharpe, beta)", 14),
        questionary.Choice("Stock Screener (S&P 500)",     15),
        questionary.Separator("─── Comparison ─────────────────────────────"),
        questionary.Choice("Compare Stocks",               16),
        questionary.Choice("Watchlist",                    17),
        questionary.Separator("─── AI (requires API key) ──────────────────"),
        questionary.Choice("\U0001f9e0  AI Analysis \u2192",    18),
        questionary.Separator("─── Utilities ──────────────────────────────"),
        questionary.Choice("Export Report to HTML",        19),
        questionary.Choice("Mutual Funds",                 20),
        questionary.Choice("Change Ticker",                21),
        questionary.Separator(),
        questionary.Choice("Exit",                         0),
    ]

    choice_key = questionary.select(
        "Select an option:",
        choices=choices,
        style=questionary.Style([
            ("qmark",       "fg:cyan bold"),
            ("question",    "bold"),
            ("answer",      "fg:green bold"),
            ("pointer",     "fg:cyan bold"),
            ("highlighted", "fg:cyan bold"),
            ("selected",    "fg:green"),
            ("separator",   "fg:#ff8700"),
        ]),
        instruction="(Use arrow keys to move, Enter to select)",
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
            # Offer deeper analysis
            deeper = questionary.select(
                "Deep dive:",
                choices=[
                    questionary.Choice("Risk Profile (volatility, VaR, drawdown, Sharpe)", "risk"),
                    questionary.Choice("Fund Analysis (expense, rolling returns, consistency)", "analyze"),
                    questionary.Choice("Skip", "skip"),
                ],
                style=questionary.Style([("pointer", "fg:cyan bold"), ("highlighted", "fg:cyan bold")]),
            ).ask()
            if deeper == "risk":
                cmd_global_fund_risk(sym)
            elif deeper == "analyze":
                cmd_global_fund_analyze(sym)


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

    _print_session_header(s)

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
  finscope AAPL risk                 Risk profile (volatility, VaR, Sharpe, beta)
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
        "risk":              lambda: cmd_risk(symbol, args[2] if len(args) > 2 else parsed.period),
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
    banner = (
        "\n"
        "  ███████╗██╗███╗   ██╗███████╗ ██████╗ ██████╗ ██████╗ ███████╗\n"
        "  ██╔════╝██║████╗  ██║██╔════╝██╔════╝██╔═══██╗██╔══██╗██╔════╝\n"
        "  █████╗  ██║██╔██╗ ██║███████╗██║     ██║   ██║██████╔╝█████╗  \n"
        "  ██╔══╝  ██║██║╚██╗██║╚════██║██║     ██║   ██║██╔═══╝ ██╔══╝  \n"
        "  ██║     ██║██║ ╚████║███████║╚██████╗╚██████╔╝██║     ███████╗\n"
        "  ╚═╝     ╚═╝╚═╝  ╚═══╝╚══════╝ ╚═════╝ ╚═════╝ ╚═╝     ╚══════╝\n"
    )
    console.print(f"[bold cyan]{banner}[/bold cyan]")
    console.print(Rule(style="cyan"))
    console.print(
        "  [dim]Terminal-based financial research · "
        "Yahoo Finance · SEC EDGAR · MFAPI.in[/dim]"
    )
    console.print(Rule(style="cyan"))
    console.print()


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
