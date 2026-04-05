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
)
from dashboard.ui import (
    render_header,
    render_description,
    render_ratios,
    render_price_history,
    render_financials,
    render_news,
)

console = Console()

MENU = {
    1: "Company Overview",
    2: "Key Ratios",
    3: "Price History",
    4: "Income Statement",
    5: "Balance Sheet",
    6: "Cash Flow",
    7: "News",
    8: "Change Ticker",
    0: "Exit",
}


def show_menu():
    """Display the interactive menu."""
    console.print()
    console.print(Rule("Menu", style="blue"))
    for key, label in MENU.items():
        if key == 0:
            console.print(f"  [red][{key}][/red] {label}")
        else:
            console.print(f"  [cyan][{key}][/cyan] {label}")
    console.print()


def run_dashboard(symbol: str):
    """Main dashboard loop for a given ticker symbol."""
    console.print(f"\nLoading data for [bold cyan]{symbol.upper()}[/bold cyan]...\n")

    ticker = get_ticker(symbol)
    info = get_company_info(ticker)

    if not info or info.get("quoteType") is None:
        console.print(f"[red]Could not find ticker: {symbol}[/red]")
        return False

    render_header(info)

    while True:
        show_menu()
        choice = IntPrompt.ask("Select an option", default=1)

        if choice == 0:
            console.print("[dim]Goodbye.[/dim]")
            sys.exit(0)

        elif choice == 1:
            render_header(info)
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
            render_price_history(df, period)

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
            args.symbol = None  # Only use CLI arg on first run
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
