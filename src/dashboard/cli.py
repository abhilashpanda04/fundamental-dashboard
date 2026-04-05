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
)

console = Console()

MENU = {
    1: "Company Overview",
    2: "Key Ratios",
    3: "Price History (with sparkline)",
    4: "Income Statement",
    5: "Balance Sheet",
    6: "Cash Flow",
    7: "News",
    8: "Analyst Recommendations",
    9: "Major Holders",
    10: "Compare Stocks",
    11: "Watchlist",
    12: "Export Report to HTML",
    13: "Change Ticker",
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

        elif choice == 11:
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

        elif choice == 12:
            filename = Prompt.ask("Output filename", default=f"{symbol.lower()}_report.html")
            ratios = get_key_ratios(info)
            price_df = get_price_history(ticker, period="1mo")
            export_to_html(info, ratios, price_df, output_path=filename)

        elif choice == 13:
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
