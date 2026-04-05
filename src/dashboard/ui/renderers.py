"""Rich terminal renderers for the Fundamental Dashboard.

Every public function in this module takes pure data objects / dicts and
writes to the shared console.  No data fetching occurs here; renderers are
concerned only with presentation.
"""

from __future__ import annotations

import pandas as pd
from rich import box
from rich.columns import Columns
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.text import Text

from dashboard.config import config
from dashboard.ui.builders import TableBuilder, comparison_table, financial_table, simple_table
from dashboard.ui.formatters import (
    format_currency,
    format_number,
    format_pct,
    format_return,
    make_sparkline,
    safe_float,
)

console = Console()

# ── Header / Overview ─────────────────────────────────────────────────────────


def render_header(info: dict, sparkline_data: list[float] | None = None) -> None:
    """Render the company header panel with price, sector, and sparkline."""
    name = info.get("longName") or info.get("shortName", "Unknown")
    symbol = info.get("symbol", "")
    price = info.get("currentPrice") or info.get("regularMarketPrice", "N/A")
    change = info.get("regularMarketChangePercent", 0)
    currency = info.get("currency", "USD")
    sector = info.get("sector", "N/A")
    industry = info.get("industry", "N/A")
    exchange = info.get("exchange", "N/A")

    color = "green" if isinstance(change, (int, float)) and change >= 0 else "red"
    change_str = f"[{color}]{change:+.2f}%[/{color}]" if isinstance(change, (int, float)) else ""

    text = Text()
    text.append(f"{name}", style="bold white")
    text.append(f"  ({symbol})", style="dim")
    text.append(f"\n{sector} / {industry}", style="italic")
    text.append(f"\nExchange: {exchange}  |  Currency: {currency}")
    text.append(f"\n\n{currency} {price}", style=f"bold {color}")
    text.append(f"  {change_str}")

    console.print(Panel(text, title="Company Overview", border_style="blue"))

    if sparkline_data:
        spark = make_sparkline(sparkline_data, width=60)
        console.print(f"  3-Month Trend: {spark}\n")


def render_description(info: dict) -> None:
    """Render the company long description."""
    desc = info.get("longBusinessSummary", "No description available.")
    console.print(Panel(desc, title="About", border_style="dim", padding=(1, 2)))


# ── Key Ratios ────────────────────────────────────────────────────────────────


def render_ratios(ratios: dict) -> None:
    """Render key financial ratios in a two-column layout."""
    builder = (
        TableBuilder("Key Financial Ratios")
        .border("cyan")
        .column("Metric", style="bold", min_width=20)
        .column("Value", justify="right", min_width=15)
        .column("Metric", style="bold", min_width=20)
        .column("Value", justify="right", min_width=15)
    )

    items = list(ratios.items())
    for i in range(0, len(items), 2):
        left_name, left_val = items[i]
        right_name, right_val = items[i + 1] if i + 1 < len(items) else ("", None)
        builder.row(left_name, format_number(left_val), right_name, format_number(right_val))

    console.print(builder.build())


# ── Price History ─────────────────────────────────────────────────────────────


def render_price_history(
    df: pd.DataFrame, period: str, sparkline_data: list[float] | None = None
) -> None:
    """Render a price history table with optional sparkline header."""
    if df is None or df.empty:
        console.print("[yellow]No price data available.[/yellow]")
        return

    if sparkline_data:
        spark = make_sparkline(sparkline_data, width=60)
        console.print(f"\n  Price Chart ({period}): {spark}\n")

    builder = (
        simple_table(f"Price History ({period})", border="green")
        .box_style(box.SIMPLE_HEAVY)
        .column("Date", style="dim")
        .column("Open", justify="right")
        .column("High", justify="right")
        .column("Low", justify="right")
        .column("Close", justify="right", style="bold")
        .column("Volume", justify="right")
    )

    for idx, row in df.tail(config.max_price_rows).iterrows():
        date_str = idx.strftime("%Y-%m-%d") if hasattr(idx, "strftime") else str(idx)
        close_val = safe_float(row.get("Close", 0)) or 0
        open_val = safe_float(row.get("Open", 0)) or 0
        high = safe_float(row.get("High", 0)) or 0
        low = safe_float(row.get("Low", 0)) or 0
        volume = safe_float(row.get("Volume", 0)) or 0
        color = "green" if close_val >= open_val else "red"

        builder.row(
            date_str,
            f"{open_val:.2f}",
            f"{high:.2f}",
            f"{low:.2f}",
            f"[{color}]{close_val:.2f}[/{color}]",
            f"{int(volume):,}",
        )

    console.print(builder.build())


# ── Financial Statements ──────────────────────────────────────────────────────


def render_financials(df: pd.DataFrame, title: str) -> None:
    """Render an annual financial statement DataFrame as a table."""
    if df is None or df.empty:
        console.print(f"[yellow]No {title.lower()} data available.[/yellow]")
        return

    builder = financial_table(title)
    builder.column("Item", style="bold", min_width=30)

    for col in df.columns:
        date_str = col.strftime("%Y") if hasattr(col, "strftime") else str(col)
        builder.column(date_str, justify="right", min_width=14)

    for idx in df.index[:15]:
        row_data: list[str] = []
        for col in df.columns:
            val = df.loc[idx, col]
            if pd.isna(val):
                row_data.append("[dim]—[/dim]")
            elif abs(val) >= 1_000_000:
                row_data.append(f"${val / 1_000_000:.1f}M")
            else:
                row_data.append(f"{val:,.0f}")
        item_name = str(idx).replace("_", " ").title()
        builder.row(item_name, *row_data)

    console.print(builder.build())


# ── News ──────────────────────────────────────────────────────────────────────


def render_news(news: list[dict]) -> None:
    """Render recent news headlines."""
    if not news:
        console.print("[yellow]No news available.[/yellow]")
        return

    console.print(Rule("Recent News", style="yellow"))
    for i, article in enumerate(news[: config.max_news_items]):
        title = article.get("title") or article.get("content", {}).get("title", "No title")
        publisher = (
            article.get("publisher")
            or article.get("content", {}).get("provider", {}).get("displayName", "Unknown")
        )
        link = (
            article.get("link")
            or article.get("content", {}).get("canonicalUrl", {}).get("url", "")
        )

        console.print(f"\n  [bold]{i + 1}. {title}[/bold]")
        console.print(f"     [dim]{publisher}[/dim]")
        if link:
            console.print(f"     [blue underline]{link}[/blue underline]")


# ── Analyst Recommendations ───────────────────────────────────────────────────


def render_analyst_recommendations(recs: pd.DataFrame | None) -> None:
    """Render analyst sentiment as a colour-coded bar chart."""
    if recs is None or recs.empty:
        console.print("[yellow]No analyst recommendations available.[/yellow]")
        return

    console.print(Rule("Analyst Recommendations", style="cyan"))
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

    counts = {k: int(latest.get(k, 0) or 0) for k in categories}
    total = sum(counts.values())

    if total == 0:
        console.print("[yellow]No recommendation data.[/yellow]")
        return

    console.print(f"\n  Total Analysts: [bold]{total}[/bold]\n")
    for key, (label, style) in categories.items():
        count = counts[key]
        pct = (count / total) * 100
        bar = "█" * int(pct / 2)
        console.print(f"  [{style}]{label:>12}[/{style}]  [{style}]{bar}[/{style}] {count} ({pct:.0f}%)")
    console.print()


# ── Major Holders ─────────────────────────────────────────────────────────────


def render_major_holders(
    breakdown: pd.DataFrame | None,
    institutional: pd.DataFrame | None,
) -> None:
    """Render ownership breakdown and top institutional holders."""
    console.print(Rule("Major Holders", style="cyan"))

    if breakdown is not None and not breakdown.empty:
        builder = (
            TableBuilder("Ownership Breakdown")
            .border("cyan")
            .column("Category", style="bold")
            .column("Value", justify="right")
        )
        for _, row in breakdown.iterrows():
            builder.row(
                str(row.iloc[1]) if len(row) > 1 else str(row.iloc[0]),
                str(row.iloc[0]),
            )
        console.print(builder.build())

    if institutional is not None and not institutional.empty:
        builder = (
            TableBuilder("Top Institutional Holders")
            .border("green")
            .column("Holder", style="bold", min_width=30)
            .column("Shares", justify="right")
            .column("Value", justify="right")
            .column("% Out", justify="right")
        )
        for _, row in institutional.head(config.max_institutional_holders).iterrows():
            holder = str(row.get("Holder", "N/A"))
            shares = row.get("Shares", 0)
            value = row.get("Value", 0)
            pct = row.get("pctHeld") or row.get("% Out", 0)

            shares_str = f"{int(shares):,}" if pd.notna(shares) else "N/A"
            value_str = format_number(value) if pd.notna(value) else "N/A"
            pct_str = (
                f"{float(pct) * 100:.2f}%"
                if pd.notna(pct) and isinstance(pct, (int, float))
                else str(pct) if pd.notna(pct) else "N/A"
            )
            builder.row(holder, shares_str, value_str, pct_str)
        console.print(builder.build())

    if (breakdown is None or breakdown.empty) and (institutional is None or institutional.empty):
        console.print("[yellow]No holder data available.[/yellow]")


# ── Stock Comparison ──────────────────────────────────────────────────────────


def render_comparison(data: list[dict]) -> None:
    """Render side-by-side metric comparison for multiple tickers."""
    if not data:
        console.print("[yellow]No comparison data available.[/yellow]")
        return

    console.print(Rule("Stock Comparison", style="bold blue"))
    console.print()
    for item in data:
        spark = make_sparkline(item.get("sparkline", []), width=50)
        console.print(f"  [bold]{item['symbol']:>6}[/bold]  {spark}")
    console.print()

    builder = comparison_table("Side-by-Side Comparison")
    builder.column("Metric", style="bold", min_width=18)
    for item in data:
        builder.column(item["symbol"], justify="right", min_width=14)

    rows: list[tuple[str, ...]] = []
    metric_fns = [
        ("Company",      lambda d: d.get("name", "N/A")),
        ("Price",        lambda d: f"${d['price']:.2f}" if d.get("price") else "N/A"),
        ("Change %",     lambda d: format_pct(d.get("change_pct"))),
        ("Market Cap",   lambda d: format_number(d.get("market_cap"))),
        ("P/E Ratio",    lambda d: f"{d['pe_ratio']:.2f}" if d.get("pe_ratio") else "N/A"),
        ("Forward P/E",  lambda d: f"{d['forward_pe']:.2f}" if d.get("forward_pe") else "N/A"),
        ("PEG",          lambda d: f"{d['peg']:.2f}" if d.get("peg") else "N/A"),
        ("P/B",          lambda d: f"{d['pb']:.2f}" if d.get("pb") else "N/A"),
        ("P/S",          lambda d: f"{d['ps']:.2f}" if d.get("ps") else "N/A"),
        ("Profit Margin",lambda d: f"{d['profit_margin']*100:.1f}%" if d.get("profit_margin") else "N/A"),
        ("ROE",          lambda d: f"{d['roe']*100:.1f}%" if d.get("roe") else "N/A"),
        ("Debt/Equity",  lambda d: f"{d['debt_equity']:.1f}" if d.get("debt_equity") else "N/A"),
        ("Div. Yield",   lambda d: f"{d['dividend_yield']*100:.2f}%" if d.get("dividend_yield") else "N/A"),
        ("Beta",         lambda d: f"{d['beta']:.2f}" if d.get("beta") else "N/A"),
        ("Revenue",      lambda d: format_number(d.get("revenue"))),
        ("EBITDA",       lambda d: format_number(d.get("ebitda"))),
    ]

    for label, fn in metric_fns:
        rows.append((label, *[fn(d) for d in data]))

    builder.rows(rows)
    console.print(builder.build())


# ── Watchlist ─────────────────────────────────────────────────────────────────


def render_watchlist(data: list[dict]) -> None:
    """Render a compact ticker watchlist."""
    if not data:
        console.print("[yellow]No watchlist data.[/yellow]")
        return

    builder = (
        TableBuilder("Watchlist")
        .border("blue")
        .box_style(box.HEAVY_EDGE)
        .column("Ticker", style="bold cyan", min_width=8)
        .column("Name", min_width=20)
        .column("Price", justify="right", min_width=10)
        .column("Change", justify="right", min_width=10)
        .column("Mkt Cap", justify="right", min_width=12)
        .column("P/E", justify="right", min_width=8)
        .column("3M Trend", min_width=25)
    )

    for item in data:
        price = f"${item['price']:.2f}" if item.get("price") else "N/A"
        builder.row(
            item["symbol"],
            (item.get("name") or "")[:25],
            price,
            format_pct(item.get("change_pct")),
            format_number(item.get("market_cap")),
            f"{item['pe_ratio']:.1f}" if item.get("pe_ratio") else "N/A",
            make_sparkline(item.get("sparkline", []), width=20),
        )

    console.print(builder.build())


# ── HTML Export ───────────────────────────────────────────────────────────────


def export_to_html(
    info: dict,
    ratios: dict,
    price_df: pd.DataFrame,
    output_path: str = "report.html",
) -> None:
    """Export a fundamental report to an HTML file."""
    export_console = Console(record=True, width=120)

    name = info.get("longName") or info.get("shortName", "Unknown")
    symbol = info.get("symbol", "")
    price = info.get("currentPrice") or info.get("regularMarketPrice", "N/A")
    change = info.get("regularMarketChangePercent", 0)
    currency = info.get("currency", "USD")
    color = "green" if isinstance(change, (int, float)) and change >= 0 else "red"

    export_console.print(Rule(f"Fundamental Report: {name} ({symbol})", style="bold blue"))
    export_console.print(f"\n[bold]{name}[/bold] ({symbol})")
    export_console.print(f"Sector: {info.get('sector', 'N/A')} / {info.get('industry', 'N/A')}")
    export_console.print(
        f"Price: [{color}]{currency} {price} "
        + (f"({change:+.2f}%)" if isinstance(change, (int, float)) else "")
        + f"[/{color}]\n"
    )

    # Ratios
    ratio_builder = (
        TableBuilder("Key Financial Ratios")
        .column("Metric", style="bold", min_width=20)
        .column("Value", justify="right", min_width=15)
        .column("Metric", style="bold", min_width=20)
        .column("Value", justify="right", min_width=15)
    )
    items = list(ratios.items())
    for i in range(0, len(items), 2):
        left_name, left_val = items[i]
        right_name, right_val = items[i + 1] if i + 1 < len(items) else ("", None)
        ratio_builder.row(left_name, format_number(left_val), right_name, format_number(right_val))
    export_console.print(ratio_builder.build())

    # Price history
    if price_df is not None and not price_df.empty:
        price_builder = (
            simple_table("Recent Price History")
            .box_style(box.SIMPLE_HEAVY)
            .column("Date", style="dim")
            .column("Open", justify="right")
            .column("High", justify="right")
            .column("Low", justify="right")
            .column("Close", justify="right", style="bold")
            .column("Volume", justify="right")
        )
        for idx, row in price_df.tail(10).iterrows():
            date_str = idx.strftime("%Y-%m-%d") if hasattr(idx, "strftime") else str(idx)
            close_val = safe_float(row.get("Close", 0)) or 0
            open_val = safe_float(row.get("Open", 0)) or 0
            high = safe_float(row.get("High", 0)) or 0
            low = safe_float(row.get("Low", 0)) or 0
            volume = safe_float(row.get("Volume", 0)) or 0
            price_builder.row(
                date_str,
                f"{open_val:.2f}",
                f"{high:.2f}",
                f"{low:.2f}",
                f"{close_val:.2f}",
                f"{int(volume):,}",
            )
        export_console.print(price_builder.build())

    export_console.print(
        f"\n[dim]Generated on {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}[/dim]"
    )

    html = export_console.export_html()
    with open(output_path, "w", encoding="utf-8") as fh:
        fh.write(html)

    console.print(f"\n[bold green]Report exported to {output_path}[/bold green]")


# ── SEC EDGAR ─────────────────────────────────────────────────────────────────


def render_detailed_financials(data: dict, category: str) -> None:
    """Render XBRL financial data for a specific category."""
    cat_data = data.get(category)
    if not cat_data:
        console.print(f"[yellow]No {category} data available from SEC EDGAR.[/yellow]")
        return

    all_years: set = set()
    for values in cat_data.values():
        for entry in values:
            if entry.get("fy"):
                all_years.add(entry["fy"])

    years = sorted(all_years, reverse=True)[:6]

    builder = (
        financial_table(f"{category} (SEC EDGAR / 10-K Filings)")
        .column("Item", style="bold", min_width=25)
    )
    for year in years:
        builder.column(f"FY {year}", justify="right", min_width=14)

    for concept_name, values in cat_data.items():
        year_map: dict = {}
        for entry in values:
            fy = entry.get("fy")
            if fy in years:
                year_map[fy] = entry.get("val")

        is_shares = any(w in concept_name.lower() for w in ("shares", "eps", "dividend per"))
        row: list[str] = [concept_name]
        for year in years:
            val = year_map.get(year)
            if val is None:
                row.append("[dim]—[/dim]")
            elif isinstance(val, (int, float)):
                row.append(_format_xbrl_value(val, is_shares))
            else:
                row.append(str(val))

        builder.row(*row)

    console.print(builder.build())


def _format_xbrl_value(val: float, is_shares: bool) -> str:
    if is_shares:
        if abs(val) >= 1_000_000_000:
            return f"{val / 1_000_000_000:.2f}B"
        if abs(val) >= 1_000_000:
            return f"{val / 1_000_000:.1f}M"
        return f"{val:,.2f}"
    if abs(val) >= 1_000_000_000:
        return f"${val / 1_000_000_000:.2f}B"
    if abs(val) >= 1_000_000:
        return f"${val / 1_000_000:.1f}M"
    if abs(val) < 100:
        return f"{val:.2f}"
    return f"{val:,.0f}"


def render_sec_filings(filings: list[dict]) -> None:
    """Render a table of recent SEC filings."""
    if not filings:
        console.print("[yellow]No filings data available.[/yellow]")
        return

    console.print(Rule("Recent SEC Filings", style="cyan"))
    _HIGHLIGHT = {"10-K", "10-Q", "8-K", "DEF 14A", "S-1"}

    builder = (
        simple_table("", border="cyan")
        .column("Form", style="bold cyan", min_width=12)
        .column("Date", style="dim", min_width=12)
        .column("Description", min_width=30)
        .column("Link", style="blue", min_width=20)
    )

    for filing in filings:
        form = filing["form"]
        style = "bold yellow" if form in _HIGHLIGHT else ""
        desc = filing.get("description", "")[:50]
        url = filing.get("url", "")
        builder.row(
            f"[{style}]{form}[/{style}]" if style else form,
            filing["date"],
            desc,
            f"[link={url}]View[/link]" if url else "",
        )

    console.print(builder.build())


def render_insider_transactions(transactions: list[dict]) -> None:
    """Render recent Form 3/4/5 insider transactions."""
    if not transactions:
        console.print("[yellow]No insider transaction data available.[/yellow]")
        return

    console.print(Rule("Insider Transactions (Form 4)", style="yellow"))
    builder = (
        simple_table("", border="yellow")
        .column("Form", style="bold", min_width=6)
        .column("Date", style="dim", min_width=12)
        .column("Description", min_width=40)
        .column("Link", style="blue")
    )

    for txn in transactions[:15]:
        url = txn.get("url", "")
        builder.row(
            txn["form"],
            txn["date"],
            txn.get("description", "Insider transaction")[:50],
            f"[link={url}]View[/link]" if url else "",
        )

    console.print(builder.build())


# ── Mutual Funds ──────────────────────────────────────────────────────────────


def render_india_fund_overview(
    meta: dict, _returns: dict, nav_data: list[dict]
) -> None:
    """Render an Indian mutual fund overview panel."""
    name = meta.get("scheme_name", "Unknown")
    fund_house = meta.get("fund_house", "N/A")
    category = meta.get("scheme_category", "N/A")
    scheme_type = meta.get("scheme_type", "N/A")
    isin = meta.get("isin_growth", "N/A")

    current_nav = float(nav_data[0]["nav"]) if nav_data else 0
    nav_date = nav_data[0]["date"] if nav_data else "N/A"

    text = Text()
    text.append(f"{name}\n", style="bold white")
    text.append(f"Fund House: {fund_house}\n", style="yellow")
    text.append(f"Category:   {category}\n", style="italic cyan")
    text.append(f"Type:       {scheme_type}\n", style="dim")
    text.append(f"ISIN:       {isin}\n", style="dim")
    text.append("\nLatest NAV: ", style="bold")
    text.append(f"₹{current_nav:.4f}", style="bold green")
    text.append(f"  (as of {nav_date})", style="dim")

    console.print(Panel(text, title="Indian Mutual Fund", border_style="green"))


def render_fund_returns(returns: dict, title: str = "Returns") -> None:
    """Render fund returns for multiple periods."""
    if not returns:
        console.print("[yellow]No return data available.[/yellow]")
        return

    builder = (
        TableBuilder(title)
        .border("green")
        .column("Period", style="bold", min_width=10)
        .column("Return", justify="right", min_width=12)
        .column("Start NAV", justify="right", min_width=14)
        .column("Current NAV", justify="right", min_width=14)
        .column("Start Date", style="dim", min_width=14)
    )

    for period, data in returns.items():
        if not isinstance(data, dict):
            continue
        pct = data.get("return_pct")
        color = "green" if pct and pct >= 0 else "red"
        start_nav = data.get("start_nav")
        current_nav = data.get("current_nav")
        start_date = data.get("start_date", "N/A")

        pct_str = f"[{color}]{pct:+.2f}%[/{color}]" if pct is not None else "[dim]N/A[/dim]"
        start_nav_str = f"₹{start_nav:.4f}" if start_nav else "N/A"
        cur_nav_str = f"₹{current_nav:.4f}" if current_nav else "N/A"

        builder.row(period, pct_str, start_nav_str, cur_nav_str, start_date)

    console.print(builder.build())


def render_india_fund_search_results(results: list[dict]) -> None:
    """Render Indian mutual fund search results."""
    if not results:
        console.print("[yellow]No funds found matching your search.[/yellow]")
        return

    builder = (
        TableBuilder("Search Results")
        .border("green")
        .column("#", style="dim", min_width=4)
        .column("Scheme Code", style="bold cyan", min_width=12)
        .column("Fund Name", min_width=55)
    )

    for i, fund in enumerate(results[:20], 1):
        builder.row(str(i), str(fund["schemeCode"]), fund["schemeName"])

    console.print(builder.build())


def render_global_fund_snapshot(data: list[dict], region: str) -> None:
    """Render a snapshot table of global ETFs / mutual funds."""
    if not data:
        console.print("[yellow]No fund data available.[/yellow]")
        return

    builder = (
        TableBuilder(f"{region} Funds / ETFs")
        .border("blue")
        .box_style(box.HEAVY_EDGE)
        .column("Symbol", style="bold cyan", min_width=10)
        .column("Name", min_width=30)
        .column("NAV / Price", justify="right", min_width=12)
        .column("Day Chg", justify="right", min_width=10)
        .column("AUM", justify="right", min_width=12)
        .column("Expense", justify="right", min_width=10)
        .column("YTD", justify="right", min_width=10)
        .column("1Y Trend", min_width=22)
    )

    for fund in data:
        nav = fund.get("nav")
        currency = fund.get("currency", "")
        nav_str = format_currency(nav, currency) if nav else "[dim]N/A[/dim]"

        expense = fund.get("expense_ratio")
        expense_str = f"{float(expense)*100:.2f}%" if expense else "[dim]N/A[/dim]"

        ytd = fund.get("ytd_return")
        ytd_str = format_return(ytd)

        change = fund.get("change_pct")
        change_str = format_return(change / 100 if change is not None else None)

        builder.row(
            fund["symbol"],
            (fund.get("description") or fund.get("name", ""))[:30],
            nav_str,
            change_str,
            format_currency(fund.get("total_assets")),
            expense_str,
            ytd_str,
            make_sparkline(fund.get("sparkline", []), width=18),
        )

    console.print(builder.build())


def render_global_fund_detail(
    symbol: str, info: dict, returns: dict, sparkline: list[float]
) -> None:
    """Render a detailed view of a global mutual fund or ETF."""
    name = info.get("longName") or info.get("shortName") or symbol
    currency = info.get("currency", "USD")
    nav = info.get("navPrice") or info.get("currentPrice") or info.get("previousClose")
    change = info.get("regularMarketChangePercent", 0)
    fund_family = info.get("fundFamily") or info.get("issuer", "N/A")
    category = info.get("category") or info.get("fundInceptionDate", "N/A")
    total_assets = info.get("totalAssets")
    expense = info.get("annualReportExpenseRatio")
    beta = info.get("beta3Year") or info.get("beta")
    morningstar = info.get("morningStarOverallRating")
    inception = info.get("fundInceptionDate")

    color = "green" if isinstance(change, (int, float)) and change >= 0 else "red"

    text = Text()
    text.append(f"{name}\n", style="bold white")
    text.append(f"Symbol: {symbol}  |  Fund Family: {fund_family}\n", style="dim")
    if category and category != "N/A":
        text.append(f"Category: {category}\n", style="italic cyan")
    text.append(f"\n{currency} {nav}  ", style=f"bold {color}")
    if isinstance(change, (int, float)):
        text.append(f"[{color}]{change:+.2f}%[/{color}]")

    meta_parts = []
    if total_assets:
        meta_parts.append(f"AUM: {format_currency(total_assets)}")
    if expense:
        meta_parts.append(f"Expense: {float(expense)*100:.4f}%")
    if beta:
        meta_parts.append(f"Beta(3Y): {beta:.2f}")
    if morningstar:
        meta_parts.append(f"Morningstar: {'★' * int(morningstar)}")
    if inception:
        meta_parts.append(f"Inception: {inception}")
    if meta_parts:
        text.append(f"\n{' | '.join(meta_parts)}", style="dim")

    console.print(Panel(text, title=f"Fund Overview — {symbol}", border_style="blue"))
    if sparkline:
        console.print(f"  1Y Trend: {make_sparkline(sparkline, width=60)}\n")

    if returns:
        ret_builder = (
            TableBuilder("Returns")
            .border("green")
            .column("Period", style="bold", min_width=12)
            .column("Return", justify="right", min_width=12)
        )
        for period, val in returns.items():
            if val is not None:
                ret_builder.row(period, format_return(val / 100 if abs(float(val)) > 1 else val))
        console.print(ret_builder.build())
