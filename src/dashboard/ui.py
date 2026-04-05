"""Rich terminal rendering for the dashboard."""

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns
from rich.text import Text
from rich.layout import Layout
from rich.rule import Rule
from rich.bar import Bar
from rich import box
import pandas as pd

console = Console()

# ──────────────────────────────────────────────────────────────
# Sparkline
# ──────────────────────────────────────────────────────────────

SPARK_CHARS = "▁▂▃▄▅▆▇█"


def _make_sparkline(values: list[float], width: int = 40) -> str:
    """Generate an ASCII sparkline string from a list of floats."""
    if not values or len(values) < 2:
        return "[dim]No data[/dim]"

    # Downsample if needed
    if len(values) > width:
        step = len(values) / width
        values = [values[int(i * step)] for i in range(width)]

    mn, mx = min(values), max(values)
    rng = mx - mn if mx != mn else 1

    spark = ""
    for v in values:
        idx = int((v - mn) / rng * (len(SPARK_CHARS) - 1))
        spark += SPARK_CHARS[idx]

    # Color based on overall trend
    color = "green" if values[-1] >= values[0] else "red"
    pct_change = ((values[-1] - values[0]) / values[0]) * 100

    return f"[{color}]{spark}[/{color}]  [{color}]{pct_change:+.1f}%[/{color}]"


# ──────────────────────────────────────────────────────────────
# Formatting helpers
# ──────────────────────────────────────────────────────────────

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


def _format_pct(value) -> str:
    """Format a percentage value with color."""
    if value is None:
        return "[dim]N/A[/dim]"
    color = "green" if value >= 0 else "red"
    return f"[{color}]{value:+.2f}%[/{color}]"


def _safe_float(val):
    """Safely extract a float from a possibly nested yfinance value."""
    if val is None:
        return None
    if hasattr(val, '__iter__') and not isinstance(val, str):
        vals = list(val)
        return float(vals[0]) if vals else None
    return float(val)


# ──────────────────────────────────────────────────────────────
# Header and Overview
# ──────────────────────────────────────────────────────────────

def render_header(info: dict, sparkline_data: list[float] | None = None):
    """Render the company header with name, sector, current price, and sparkline."""
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
    price_text.append(
        f"\n{currency} {price}",
        style="bold green" if isinstance(change, (int, float)) and change >= 0 else "bold red",
    )
    price_text.append(f"  {change_str}")

    content = header_text + price_text

    if sparkline_data:
        spark = _make_sparkline(sparkline_data)
        content.append(f"\n\n3-Month Trend: ")
        console.print(Panel(content, title="Company Overview", border_style="blue"))
        console.print(f"  3-Month Trend: {spark}\n")
    else:
        console.print(Panel(content, title="Company Overview", border_style="blue"))


def render_description(info: dict):
    """Render the company description."""
    desc = info.get("longBusinessSummary", "No description available.")
    console.print(Panel(desc, title="About", border_style="dim", padding=(1, 2)))


# ──────────────────────────────────────────────────────────────
# Key Ratios
# ──────────────────────────────────────────────────────────────

def render_ratios(ratios: dict):
    """Render key financial ratios in a two-column table."""
    table = Table(title="Key Financial Ratios", box=box.ROUNDED, border_style="cyan")
    table.add_column("Metric", style="bold", min_width=20)
    table.add_column("Value", justify="right", min_width=15)
    table.add_column("Metric", style="bold", min_width=20)
    table.add_column("Value", justify="right", min_width=15)

    items = list(ratios.items())

    for i in range(0, len(items), 2):
        left_name, left_val = items[i]
        if i + 1 < len(items):
            right_name, right_val = items[i + 1]
        else:
            right_name, right_val = "", None

        table.add_row(left_name, _format_number(left_val), right_name, _format_number(right_val))

    console.print(table)


# ──────────────────────────────────────────────────────────────
# Price History
# ──────────────────────────────────────────────────────────────

def render_price_history(df: pd.DataFrame, period: str, sparkline_data: list[float] | None = None):
    """Render recent price history as a table with optional sparkline."""
    if df.empty:
        console.print("[yellow]No price data available.[/yellow]")
        return

    # Show sparkline above the table
    if sparkline_data:
        console.print(f"\n  Price Chart ({period}): {_make_sparkline(sparkline_data, width=60)}\n")

    table = Table(title=f"Price History ({period})", box=box.SIMPLE_HEAVY, border_style="green")
    table.add_column("Date", style="dim")
    table.add_column("Open", justify="right")
    table.add_column("High", justify="right")
    table.add_column("Low", justify="right")
    table.add_column("Close", justify="right", style="bold")
    table.add_column("Volume", justify="right")

    display_df = df.tail(15)

    for idx, row in display_df.iterrows():
        date_str = idx.strftime("%Y-%m-%d") if hasattr(idx, "strftime") else str(idx)

        close_val = _safe_float(row.get("Close", 0)) or 0
        open_val = _safe_float(row.get("Open", 0)) or 0
        high = _safe_float(row.get("High", 0)) or 0
        low = _safe_float(row.get("Low", 0)) or 0
        volume = _safe_float(row.get("Volume", 0)) or 0

        color = "green" if close_val >= open_val else "red"

        table.add_row(
            date_str,
            f"{open_val:.2f}",
            f"{high:.2f}",
            f"{low:.2f}",
            f"[{color}]{close_val:.2f}[/{color}]",
            f"{int(volume):,}",
        )

    console.print(table)


# ──────────────────────────────────────────────────────────────
# Financial Statements
# ──────────────────────────────────────────────────────────────

def render_financials(df: pd.DataFrame, title: str):
    """Render a financial statement as a table."""
    if df is None or df.empty:
        console.print(f"[yellow]No {title.lower()} data available.[/yellow]")
        return

    table = Table(title=title, box=box.ROUNDED, border_style="magenta")
    table.add_column("Item", style="bold", min_width=30)

    for col in df.columns:
        date_str = col.strftime("%Y") if hasattr(col, "strftime") else str(col)
        table.add_column(date_str, justify="right", min_width=14)

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

        item_name = str(idx).replace("_", " ").title()
        table.add_row(item_name, *row_data)

    console.print(table)


# ──────────────────────────────────────────────────────────────
# News
# ──────────────────────────────────────────────────────────────

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


# ──────────────────────────────────────────────────────────────
# Analyst Recommendations
# ──────────────────────────────────────────────────────────────

def render_analyst_recommendations(recs: pd.DataFrame | None):
    """Render analyst recommendations as a color-coded bar chart."""
    if recs is None or recs.empty:
        console.print("[yellow]No analyst recommendations available.[/yellow]")
        return

    console.print(Rule("Analyst Recommendations", style="cyan"))

    # Get the most recent period
    latest = recs.iloc[0] if len(recs) > 0 else None
    if latest is None:
        return

    categories = {
        "strongBuy": ("Strong Buy", "bold green"),
        "buy": ("Buy", "green"),
        "hold": ("Hold", "yellow"),
        "sell": ("Sell", "red"),
        "strongSell": ("Strong Sell", "bold red"),
    }

    total = 0
    counts = {}
    for key, (label, _) in categories.items():
        val = latest.get(key, 0) or 0
        counts[key] = int(val)
        total += int(val)

    if total == 0:
        console.print("[yellow]No recommendation data.[/yellow]")
        return

    console.print(f"\n  Total Analysts: [bold]{total}[/bold]\n")

    for key, (label, style) in categories.items():
        count = counts[key]
        pct = (count / total) * 100 if total > 0 else 0
        bar_width = int(pct / 2)  # Scale to ~50 chars max
        bar = "█" * bar_width
        console.print(f"  [{style}]{label:>12}[/{style}]  [{style}]{bar}[/{style}] {count} ({pct:.0f}%)")

    console.print()


# ──────────────────────────────────────────────────────────────
# Major Holders
# ──────────────────────────────────────────────────────────────

def render_major_holders(breakdown: pd.DataFrame | None, institutional: pd.DataFrame | None):
    """Render major holders information."""
    console.print(Rule("Major Holders", style="cyan"))

    if breakdown is not None and not breakdown.empty:
        table = Table(title="Ownership Breakdown", box=box.ROUNDED, border_style="cyan")
        table.add_column("Category", style="bold")
        table.add_column("Value", justify="right")

        for idx, row in breakdown.iterrows():
            table.add_row(str(row.iloc[1]) if len(row) > 1 else str(idx), str(row.iloc[0]))

        console.print(table)

    if institutional is not None and not institutional.empty:
        table = Table(title="Top Institutional Holders", box=box.ROUNDED, border_style="green")
        table.add_column("Holder", style="bold", min_width=30)
        table.add_column("Shares", justify="right")
        table.add_column("Value", justify="right")
        table.add_column("% Out", justify="right")

        for _, row in institutional.head(10).iterrows():
            holder = str(row.get("Holder", "N/A"))
            shares = row.get("Shares", 0)
            value = row.get("Value", 0)
            pct = row.get("pctHeld") or row.get("% Out", 0)

            shares_str = f"{int(shares):,}" if pd.notna(shares) else "N/A"
            value_str = _format_number(value) if pd.notna(value) else "N/A"
            pct_str = f"{float(pct) * 100:.2f}%" if pd.notna(pct) and isinstance(pct, (int, float)) else str(pct) if pd.notna(pct) else "N/A"

            table.add_row(holder, shares_str, value_str, pct_str)

        console.print(table)

    if (breakdown is None or breakdown.empty) and (institutional is None or institutional.empty):
        console.print("[yellow]No holder data available.[/yellow]")


# ──────────────────────────────────────────────────────────────
# Stock Comparison
# ──────────────────────────────────────────────────────────────

def render_comparison(data: list[dict]):
    """Render side-by-side comparison of multiple stocks."""
    if not data:
        console.print("[yellow]No comparison data available.[/yellow]")
        return

    console.print(Rule("Stock Comparison", style="bold blue"))

    # Sparklines first
    console.print()
    for item in data:
        spark = _make_sparkline(item.get("sparkline", []), width=50)
        console.print(f"  [bold]{item['symbol']:>6}[/bold]  {spark}")
    console.print()

    # Comparison table
    table = Table(title="Side-by-Side Comparison", box=box.ROUNDED, border_style="blue")
    table.add_column("Metric", style="bold", min_width=18)

    for item in data:
        table.add_column(item["symbol"], justify="right", min_width=14)

    rows = [
        ("Company", lambda d: d.get("name", "N/A")),
        ("Price", lambda d: f"${d['price']:.2f}" if d.get("price") else "N/A"),
        ("Change %", lambda d: _format_pct(d.get("change_pct"))),
        ("Market Cap", lambda d: _format_number(d.get("market_cap"))),
        ("P/E Ratio", lambda d: f"{d['pe_ratio']:.2f}" if d.get("pe_ratio") else "N/A"),
        ("Forward P/E", lambda d: f"{d['forward_pe']:.2f}" if d.get("forward_pe") else "N/A"),
        ("PEG", lambda d: f"{d['peg']:.2f}" if d.get("peg") else "N/A"),
        ("P/B", lambda d: f"{d['pb']:.2f}" if d.get("pb") else "N/A"),
        ("P/S", lambda d: f"{d['ps']:.2f}" if d.get("ps") else "N/A"),
        ("Profit Margin", lambda d: f"{d['profit_margin'] * 100:.1f}%" if d.get("profit_margin") else "N/A"),
        ("ROE", lambda d: f"{d['roe'] * 100:.1f}%" if d.get("roe") else "N/A"),
        ("Debt/Equity", lambda d: f"{d['debt_equity']:.1f}" if d.get("debt_equity") else "N/A"),
        ("Div. Yield", lambda d: f"{d['dividend_yield'] * 100:.2f}%" if d.get("dividend_yield") else "N/A"),
        ("Beta", lambda d: f"{d['beta']:.2f}" if d.get("beta") else "N/A"),
        ("Revenue", lambda d: _format_number(d.get("revenue"))),
        ("EBITDA", lambda d: _format_number(d.get("ebitda"))),
    ]

    for label, fn in rows:
        values = [fn(d) for d in data]
        table.add_row(label, *values)

    console.print(table)


# ──────────────────────────────────────────────────────────────
# Watchlist
# ──────────────────────────────────────────────────────────────

def render_watchlist(data: list[dict]):
    """Render a compact watchlist of multiple tickers."""
    if not data:
        console.print("[yellow]No watchlist data.[/yellow]")
        return

    table = Table(title="Watchlist", box=box.HEAVY_EDGE, border_style="blue")
    table.add_column("Ticker", style="bold cyan", min_width=8)
    table.add_column("Name", min_width=20)
    table.add_column("Price", justify="right", min_width=10)
    table.add_column("Change", justify="right", min_width=10)
    table.add_column("Mkt Cap", justify="right", min_width=12)
    table.add_column("P/E", justify="right", min_width=8)
    table.add_column("3M Trend", min_width=25)

    for item in data:
        price = f"${item['price']:.2f}" if item.get("price") else "N/A"
        change = _format_pct(item.get("change_pct"))
        mkt_cap = _format_number(item.get("market_cap"))
        pe = f"{item['pe_ratio']:.1f}" if item.get("pe_ratio") else "N/A"
        spark = _make_sparkline(item.get("sparkline", []), width=20)

        table.add_row(item["symbol"], item.get("name", "")[:25], price, change, mkt_cap, pe, spark)

    console.print(table)


# ──────────────────────────────────────────────────────────────
# Export to HTML
# ──────────────────────────────────────────────────────────────

def export_to_html(info: dict, ratios: dict, price_df: pd.DataFrame, output_path: str = "report.html"):
    """Export the current dashboard view to an HTML file."""
    export_console = Console(record=True, width=120)

    name = info.get("longName", info.get("shortName", "Unknown"))
    symbol = info.get("symbol", "")

    export_console.print(Rule(f"Fundamental Report: {name} ({symbol})", style="bold blue"))

    # Header
    price = info.get("currentPrice") or info.get("regularMarketPrice", "N/A")
    change = info.get("regularMarketChangePercent", 0)
    currency = info.get("currency", "USD")
    color = "green" if isinstance(change, (int, float)) and change >= 0 else "red"

    export_console.print(f"\n[bold]{name}[/bold] ({symbol})")
    export_console.print(f"Sector: {info.get('sector', 'N/A')} / {info.get('industry', 'N/A')}")
    export_console.print(f"Price: [{color}]{currency} {price} ({change:+.2f}%)[/{color}]\n")

    # Ratios table
    table = Table(title="Key Financial Ratios", box=box.ROUNDED)
    table.add_column("Metric", style="bold", min_width=20)
    table.add_column("Value", justify="right", min_width=15)
    table.add_column("Metric", style="bold", min_width=20)
    table.add_column("Value", justify="right", min_width=15)

    items = list(ratios.items())
    for i in range(0, len(items), 2):
        left_name, left_val = items[i]
        if i + 1 < len(items):
            right_name, right_val = items[i + 1]
        else:
            right_name, right_val = "", None
        table.add_row(left_name, _format_number(left_val), right_name, _format_number(right_val))
    export_console.print(table)

    # Price history
    if price_df is not None and not price_df.empty:
        price_table = Table(title="Recent Price History", box=box.SIMPLE_HEAVY)
        price_table.add_column("Date", style="dim")
        price_table.add_column("Open", justify="right")
        price_table.add_column("High", justify="right")
        price_table.add_column("Low", justify="right")
        price_table.add_column("Close", justify="right", style="bold")
        price_table.add_column("Volume", justify="right")

        for idx, row in price_df.tail(10).iterrows():
            date_str = idx.strftime("%Y-%m-%d") if hasattr(idx, "strftime") else str(idx)
            close_val = _safe_float(row.get("Close", 0)) or 0
            open_val = _safe_float(row.get("Open", 0)) or 0
            high = _safe_float(row.get("High", 0)) or 0
            low = _safe_float(row.get("Low", 0)) or 0
            volume = _safe_float(row.get("Volume", 0)) or 0

            price_table.add_row(
                date_str, f"{open_val:.2f}", f"{high:.2f}", f"{low:.2f}",
                f"{close_val:.2f}", f"{int(volume):,}",
            )
        export_console.print(price_table)

    export_console.print(f"\n[dim]Generated on {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}[/dim]")

    html = export_console.export_html()
    with open(output_path, "w") as f:
        f.write(html)

    console.print(f"\n[bold green]Report exported to {output_path}[/bold green]")


# ──────────────────────────────────────────────────────────────
# SEC EDGAR: Detailed Financials (XBRL)
# ──────────────────────────────────────────────────────────────

def render_detailed_financials(data: dict, category: str):
    """Render detailed financials from SEC EDGAR XBRL data.

    Args:
        data: Output from sec_edgar.get_detailed_financials().
        category: One of 'Income Statement', 'Balance Sheet', 'Cash Flow', 'Per Share & Other'.
    """
    cat_data = data.get(category)
    if not cat_data:
        console.print(f"[yellow]No {category} data available from SEC EDGAR.[/yellow]")
        return

    # Collect all unique fiscal years
    all_years = set()
    for concept_values in cat_data.values():
        for entry in concept_values:
            fy = entry.get("fy")
            if fy:
                all_years.add(fy)

    years = sorted(all_years, reverse=True)[:6]  # Last 6 years

    table = Table(
        title=f"{category} (SEC EDGAR / 10-K Filings)",
        box=box.ROUNDED,
        border_style="magenta",
    )
    table.add_column("Item", style="bold", min_width=25)

    for year in years:
        table.add_column(f"FY {year}", justify="right", min_width=14)

    for concept_name, values in cat_data.items():
        # Build year -> value map (use the latest entry per fiscal year)
        year_map = {}
        for entry in values:
            fy = entry.get("fy")
            if fy in years:
                year_map[fy] = entry.get("val")

        row = [concept_name]
        for year in years:
            val = year_map.get(year)
            if val is None:
                row.append("[dim]—[/dim]")
            elif isinstance(val, (int, float)):
                if abs(val) >= 1_000_000_000:
                    row.append(f"${val / 1_000_000_000:.2f}B")
                elif abs(val) >= 1_000_000:
                    row.append(f"${val / 1_000_000:.1f}M")
                elif abs(val) < 100:
                    row.append(f"{val:.2f}")
                else:
                    row.append(f"{val:,.0f}")
            else:
                row.append(str(val))

        table.add_row(*row)

    console.print(table)


# ──────────────────────────────────────────────────────────────
# SEC EDGAR: Recent Filings
# ──────────────────────────────────────────────────────────────

def render_sec_filings(filings: list[dict]):
    """Render a table of recent SEC filings with links."""
    if not filings:
        console.print("[yellow]No filings data available.[/yellow]")
        return

    console.print(Rule("Recent SEC Filings", style="cyan"))

    table = Table(box=box.SIMPLE_HEAVY, border_style="cyan")
    table.add_column("Form", style="bold cyan", min_width=12)
    table.add_column("Date", style="dim", min_width=12)
    table.add_column("Description", min_width=30)
    table.add_column("Link", style="blue", min_width=20)

    # Highlight important filing types
    highlight_forms = {"10-K", "10-Q", "8-K", "DEF 14A", "S-1"}

    for filing in filings:
        form = filing["form"]
        style = "bold yellow" if form in highlight_forms else ""
        desc = filing.get("description", "")[:50]
        url = filing.get("url", "")

        table.add_row(
            f"[{style}]{form}[/{style}]" if style else form,
            filing["date"],
            desc,
            f"[link={url}]View[/link]" if url else "",
        )

    console.print(table)


# ──────────────────────────────────────────────────────────────
# SEC EDGAR: Insider Transactions
# ──────────────────────────────────────────────────────────────

def render_insider_transactions(transactions: list[dict]):
    """Render recent insider transactions (Form 3/4/5)."""
    if not transactions:
        console.print("[yellow]No insider transaction data available.[/yellow]")
        return

    console.print(Rule("Insider Transactions (Form 4)", style="yellow"))

    table = Table(box=box.SIMPLE_HEAVY, border_style="yellow")
    table.add_column("Form", style="bold", min_width=6)
    table.add_column("Date", style="dim", min_width=12)
    table.add_column("Description", min_width=40)
    table.add_column("Link", style="blue")

    for txn in transactions[:15]:
        url = txn.get("url", "")
        table.add_row(
            txn["form"],
            txn["date"],
            txn.get("description", "Insider transaction")[:50],
            f"[link={url}]View[/link]" if url else "",
        )

    console.print(table)
