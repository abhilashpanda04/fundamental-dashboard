"""Rich terminal rendering for the dashboard."""

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns
from rich.text import Text
from rich.layout import Layout
from rich.rule import Rule
from rich import box
import pandas as pd

console = Console()


def _format_number(value) -> str:
    """Format a number for display."""
    if value is None:
        return "[dim]N/A[/dim]"
    if isinstance(value, float):
        if abs(value) < 1:
            return f"{value:.4f}"
        if abs(value) >= 1_000_000_000:
            return f"${value / 1_000_000_000:.2f}B"
        if abs(value) >= 1_000_000:
            return f"${value / 1_000_000:.2f}M"
        return f"{value:.2f}"
    return str(value)


def render_header(info: dict):
    """Render the company header with name, sector, and current price."""
    name = info.get("longName", info.get("shortName", "Unknown"))
    symbol = info.get("symbol", "")
    price = info.get("currentPrice") or info.get("regularMarketPrice", "N/A")
    change = info.get("regularMarketChangePercent", 0)
    currency = info.get("currency", "USD")

    if isinstance(change, (int, float)):
        color = "green" if change >= 0 else "red"
        change_str = f"[{color}]{change:+.2f}%[/{color}]"
    else:
        change_str = ""

    sector = info.get("sector", "N/A")
    industry = info.get("industry", "N/A")
    exchange = info.get("exchange", "N/A")

    header_text = Text()
    header_text.append(f"{name}", style="bold white")
    header_text.append(f"  ({symbol})", style="dim")
    header_text.append(f"\n{sector} / {industry}", style="italic")
    header_text.append(f"\nExchange: {exchange}  |  Currency: {currency}")

    price_text = Text()
    price_text.append(f"\n{currency} {price}", style="bold green" if isinstance(change, (int, float)) and change >= 0 else "bold red")
    price_text.append(f"  {change_str}")

    console.print(Panel(header_text + price_text, title="Company Overview", border_style="blue"))


def render_description(info: dict):
    """Render the company description."""
    desc = info.get("longBusinessSummary", "No description available.")
    console.print(Panel(desc, title="About", border_style="dim", padding=(1, 2)))


def render_ratios(ratios: dict):
    """Render key financial ratios in a two-column table."""
    table = Table(title="Key Financial Ratios", box=box.ROUNDED, border_style="cyan")
    table.add_column("Metric", style="bold", min_width=20)
    table.add_column("Value", justify="right", min_width=15)
    table.add_column("Metric", style="bold", min_width=20)
    table.add_column("Value", justify="right", min_width=15)

    items = list(ratios.items())

    # Pair up items into two columns per row
    for i in range(0, len(items), 2):
        left_name, left_val = items[i]
        if i + 1 < len(items):
            right_name, right_val = items[i + 1]
        else:
            right_name, right_val = "", None

        table.add_row(left_name, _format_number(left_val), right_name, _format_number(right_val))

    console.print(table)


def render_price_history(df: pd.DataFrame, period: str):
    """Render recent price history as a table."""
    if df.empty:
        console.print("[yellow]No price data available.[/yellow]")
        return

    table = Table(title=f"Price History ({period})", box=box.SIMPLE_HEAVY, border_style="green")
    table.add_column("Date", style="dim")
    table.add_column("Open", justify="right")
    table.add_column("High", justify="right")
    table.add_column("Low", justify="right")
    table.add_column("Close", justify="right", style="bold")
    table.add_column("Volume", justify="right")

    # Show last 15 rows
    display_df = df.tail(15)

    for idx, row in display_df.iterrows():
        date_str = idx.strftime("%Y-%m-%d") if hasattr(idx, "strftime") else str(idx)

        # Color close based on open vs close
        close_val = row.get("Close", 0)
        open_val = row.get("Open", 0)

        # Handle MultiIndex columns from yfinance
        if hasattr(close_val, '__iter__') and not isinstance(close_val, str):
            close_val = list(close_val)[0] if len(list(close_val)) > 0 else 0
        if hasattr(open_val, '__iter__') and not isinstance(open_val, str):
            open_val = list(open_val)[0] if len(list(open_val)) > 0 else 0

        color = "green" if close_val >= open_val else "red"

        volume = row.get("Volume", 0)
        if hasattr(volume, '__iter__') and not isinstance(volume, str):
            volume = list(volume)[0] if len(list(volume)) > 0 else 0

        high = row.get("High", 0)
        low = row.get("Low", 0)
        if hasattr(high, '__iter__') and not isinstance(high, str):
            high = list(high)[0] if len(list(high)) > 0 else 0
        if hasattr(low, '__iter__') and not isinstance(low, str):
            low = list(low)[0] if len(list(low)) > 0 else 0

        table.add_row(
            date_str,
            f"{float(open_val):.2f}",
            f"{float(high):.2f}",
            f"{float(low):.2f}",
            f"[{color}]{float(close_val):.2f}[/{color}]",
            f"{int(float(volume)):,}",
        )

    console.print(table)


def render_financials(df: pd.DataFrame, title: str):
    """Render a financial statement (income, balance sheet, cashflow) as a table."""
    if df is None or df.empty:
        console.print(f"[yellow]No {title.lower()} data available.[/yellow]")
        return

    table = Table(title=title, box=box.ROUNDED, border_style="magenta")
    table.add_column("Item", style="bold", min_width=30)

    # Columns are dates
    for col in df.columns:
        date_str = col.strftime("%Y") if hasattr(col, "strftime") else str(col)
        table.add_column(date_str, justify="right", min_width=14)

    # Show top 15 rows to keep it readable
    for idx in df.index[:15]:
        row_data = []
        for col in df.columns:
            val = df.loc[idx, col]
            if pd.isna(val):
                row_data.append("[dim]—[/dim]")
            elif abs(val) >= 1_000_000:
                row_data.append(f"${val / 1_000_000:.1f}M")
            else:
                row_data.append(f"{val:,.0f}")

        # Clean up the index name
        item_name = str(idx).replace("_", " ").title()
        table.add_row(item_name, *row_data)

    console.print(table)


def render_news(news: list[dict]):
    """Render recent news articles."""
    if not news:
        console.print("[yellow]No news available.[/yellow]")
        return

    console.print(Rule("Recent News", style="yellow"))

    for i, article in enumerate(news[:8]):
        title = article.get("title") or article.get("content", {}).get("title", "No title")
        publisher = article.get("publisher") or article.get("content", {}).get("provider", {}).get("displayName", "Unknown")
        link = article.get("link") or article.get("content", {}).get("canonicalUrl", {}).get("url", "")

        console.print(f"\n  [bold]{i + 1}. {title}[/bold]")
        console.print(f"     [dim]{publisher}[/dim]")
        if link:
            console.print(f"     [blue underline]{link}[/blue underline]")
