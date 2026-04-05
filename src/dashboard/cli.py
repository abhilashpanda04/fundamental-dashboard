"""CLI entry point for the Fundamental Dashboard."""

import argparse
import sys

from rich.console import Console
from rich.prompt import Prompt, IntPrompt
from rich.rule import Rule

from dashboard.data import (
    get_ticker,
    get_company_info,
    get_key_ratios,
    get_price_history,
    get_financials,
    get_balance_sheet,
    get_cashflow,
    get_news,
    get_sparkline_data,
    get_analyst_recommendations,
    get_major_holders,
    get_comparison_data,
)
from dashboard.sec_edgar import (
    get_detailed_financials,
    get_recent_filings,
    get_insider_transactions,
)
from dashboard.mutual_funds import (
    search_india_funds,
    get_india_fund_detail,
    calculate_india_fund_returns,
    get_india_fund_nav_series,
    get_global_fund_info,
    get_global_fund_returns,
    get_global_fund_sparkline,
    get_popular_funds_snapshot,
    POPULAR_FUNDS,
)
from dashboard.ui import (
    render_header,
    render_description,
    render_ratios,
    render_price_history,
    render_financials,
    render_news,
    render_analyst_recommendations,
    render_major_holders,
    render_comparison,
    render_watchlist,
    export_to_html,
    render_detailed_financials,
    render_sec_filings,
    render_insider_transactions,
    render_india_fund_overview,
    render_fund_returns,
    render_india_fund_search_results,
    render_global_fund_snapshot,
    render_global_fund_detail,
    _make_sparkline,
)

console = Console()

MENU = {
    1: "Company Overview",
    2: "Key Ratios",
    3: "Price History (with sparkline)",
    4: "Income Statement (Yahoo)",
    5: "Balance Sheet (Yahoo)",
    6: "Cash Flow (Yahoo)",
    7: "News",
    8: "Analyst Recommendations",
    9: "Major Holders",
    10: "SEC EDGAR: Detailed Financials (XBRL)",
    11: "SEC EDGAR: Recent Filings",
    12: "SEC EDGAR: Insider Transactions",
    13: "Compare Stocks",
    14: "Watchlist",
    15: "Export Report to HTML",
    16: "Mutual Funds",
    17: "Change Ticker",
    0: "Exit",
}


def show_menu():
    """Display the interactive menu."""
    console.print()
    console.print(Rule("Menu", style="blue"))
    for key, label in MENU.items():
        if key == 0:
            console.print(f"  [red][{key:>2}][/red] {label}")
        else:
            console.print(f"  [cyan][{key:>2}][/cyan] {label}")
    console.print()


MF_MENU = {
    1: "India — Search & Explore (MFAPI.in)",
    2: "US Mutual Funds Snapshot",
    3: "Global ETF Snapshot (LSE)",
    4: "Asia Pacific ETF Snapshot",
    5: "European ETF Snapshot",
    6: "Fixed Income / Bond ETF Snapshot",
    7: "Lookup Any Fund / ETF by Ticker",
    0: "Back",
}


def run_mutual_funds_menu():
    """Mutual funds sub-menu."""
    while True:
        console.print()
        console.print(Rule("Mutual Funds", style="bold green"))
        for key, label in MF_MENU.items():
            style = "red" if key == 0 else "cyan"
            console.print(f"  [{style}][{key}][/{style}] {label}")
        console.print()

        choice = IntPrompt.ask("Select", default=0)

        if choice == 0:
            return

        elif choice == 1:
            _india_fund_flow()

        elif choice in (2, 3, 4, 5, 6):
            region_map = {
                2: "US",
                3: "Global ETF (LSE)",
                4: "Asia Pacific ETF",
                5: "European ETF",
                6: "Fixed Income / Bond ETF",
            }
            region = region_map[choice]
            console.print(f"\nLoading {region} funds...")
            data = get_popular_funds_snapshot(region)
            render_global_fund_snapshot(data, region)

        elif choice == 7:
            sym = Prompt.ask("Enter fund/ETF ticker (e.g., VWRL.L, INDA, AGG)")
            if not sym.strip():
                continue
            sym = sym.strip().upper()
            console.print(f"Loading data for {sym}...")
            fund_info = get_global_fund_info(sym)
            if not fund_info:
                console.print(f"[red]Could not find fund: {sym}[/red]")
                continue
            returns = get_global_fund_returns(sym)
            spark = get_global_fund_sparkline(sym, "1y")
            render_global_fund_detail(sym, fund_info, returns, spark)

        else:
            console.print("[red]Invalid option.[/red]")


def _india_fund_flow():
    """Interactive flow for searching and exploring Indian mutual funds."""
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

        elif sub == 1:
            query = Prompt.ask("Search (e.g., SBI Small Cap, Parag Parikh, HDFC Mid)")
            if not query.strip():
                continue
            results = search_india_funds(query.strip())
            render_india_fund_search_results(results)
            if not results:
                continue

            code = Prompt.ask("Enter scheme code to view details (or press Enter to skip)", default="")
            if code.strip():
                _show_india_fund(code.strip())

        elif sub == 2:
            code = Prompt.ask("Enter scheme code (e.g., 125497)")
            if code.strip():
                _show_india_fund(code.strip())


def _show_india_fund(scheme_code: str):
    """Fetch and display details for an Indian mutual fund."""
    console.print(f"\nLoading scheme {scheme_code}...")
    detail = get_india_fund_detail(scheme_code)

    if not detail:
        console.print(f"[red]Could not fetch fund {scheme_code}.[/red]")
        return

    meta = detail.get("meta", {})
    nav_data = detail.get("data", [])

    render_india_fund_overview(meta, {}, nav_data)

    # Calculate returns
    returns = calculate_india_fund_returns(nav_data)
    render_fund_returns(returns, title="Point-to-Point Returns")

    # Sparkline
    spark_vals = get_india_fund_nav_series(nav_data, days=365)
    if spark_vals:
        console.print(f"  1Y NAV Trend: {_make_sparkline(spark_vals, width=60)}")


def run_dashboard(symbol: str):
    """Main dashboard loop for a given ticker symbol."""
    console.print(f"\nLoading data for [bold cyan]{symbol.upper()}[/bold cyan]...\n")

    ticker = get_ticker(symbol)
    info = get_company_info(ticker)

    if not info or info.get("quoteType") is None:
        console.print(f"[red]Could not find ticker: {symbol}[/red]")
        return False

    sparkline_data = get_sparkline_data(ticker, "3mo")
    render_header(info, sparkline_data)

    while True:
        show_menu()
        choice = IntPrompt.ask("Select an option", default=1)

        if choice == 0:
            console.print("[dim]Goodbye.[/dim]")
            sys.exit(0)

        elif choice == 1:
            render_header(info, sparkline_data)
            render_description(info)

        elif choice == 2:
            ratios = get_key_ratios(info)
            render_ratios(ratios)

        elif choice == 3:
            period = Prompt.ask(
                "Period",
                choices=["1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "max"],
                default="1mo",
            )
            df = get_price_history(ticker, period=period)
            period_sparkline = get_sparkline_data(ticker, period)
            render_price_history(df, period, period_sparkline)

        elif choice == 4:
            df = get_financials(ticker)
            render_financials(df, "Income Statement")

        elif choice == 5:
            df = get_balance_sheet(ticker)
            render_financials(df, "Balance Sheet")

        elif choice == 6:
            df = get_cashflow(ticker)
            render_financials(df, "Cash Flow Statement")

        elif choice == 7:
            news = get_news(ticker)
            render_news(news)

        elif choice == 8:
            recs = get_analyst_recommendations(ticker)
            render_analyst_recommendations(recs)

        elif choice == 9:
            breakdown, institutional = get_major_holders(ticker)
            render_major_holders(breakdown, institutional)

        elif choice == 10:
            console.print("Loading detailed financials from SEC EDGAR...")
            edgar_data = get_detailed_financials(symbol)
            if not edgar_data:
                console.print("[red]No SEC EDGAR data found for this ticker.[/red]")
                continue
            sub = Prompt.ask(
                "Category",
                choices=["income", "comprehensive", "assets", "liabilities", "cashflow", "pershare", "debt"],
                default="income",
            )
            cat_map = {
                "income": "Income Statement",
                "comprehensive": "Comprehensive Income",
                "assets": "Balance Sheet (Assets)",
                "liabilities": "Balance Sheet (Liabilities & Equity)",
                "cashflow": "Cash Flow",
                "pershare": "Per Share & Shares",
                "debt": "Debt Maturity Schedule",
            }
            render_detailed_financials(edgar_data, cat_map[sub])

        elif choice == 11:
            console.print("Loading recent SEC filings...")
            filings = get_recent_filings(symbol, count=20)
            render_sec_filings(filings)

        elif choice == 12:
            console.print("Loading insider transactions...")
            txns = get_insider_transactions(symbol)
            render_insider_transactions(txns)

        elif choice == 13:
            input_str = Prompt.ask(
                "Enter tickers to compare (comma-separated, e.g., AAPL,MSFT,GOOGL)"
            )
            symbols = [s.strip().upper() for s in input_str.split(",") if s.strip()]
            if symbol.upper() not in symbols:
                symbols.insert(0, symbol.upper())

            if len(symbols) < 2:
                console.print("[red]Please enter at least 2 tickers to compare.[/red]")
                continue

            console.print(f"Loading comparison data for {', '.join(symbols)}...")
            comp_data = get_comparison_data(symbols)
            render_comparison(comp_data)

        elif choice == 14:
            input_str = Prompt.ask(
                "Enter watchlist tickers (comma-separated, e.g., AAPL,TSLA,NVDA,MSFT,AMZN)"
            )
            symbols = [s.strip().upper() for s in input_str.split(",") if s.strip()]

            if not symbols:
                console.print("[red]Please enter at least 1 ticker.[/red]")
                continue

            console.print(f"Loading watchlist for {', '.join(symbols)}...")
            watch_data = get_comparison_data(symbols)
            render_watchlist(watch_data)

        elif choice == 15:
            filename = Prompt.ask("Output filename", default=f"{symbol.lower()}_report.html")
            ratios = get_key_ratios(info)
            price_df = get_price_history(ticker, period="1mo")
            export_to_html(info, ratios, price_df, output_path=filename)

        elif choice == 16:
            run_mutual_funds_menu()

        elif choice == 17:
            return True  # Signal to ask for a new ticker

        else:
            console.print("[red]Invalid option.[/red]")


def main():
    parser = argparse.ArgumentParser(
        description="Terminal-based stock fundamental analysis dashboard."
    )
    parser.add_argument("symbol", nargs="?", help="Stock ticker symbol (e.g., AAPL, MSFT)")
    args = parser.parse_args()

    console.print(Rule("Fundamental Dashboard", style="bold blue"))
    console.print("[dim]A terminal-based stock analysis tool powered by Yahoo Finance and Rich[/dim]\n")

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
