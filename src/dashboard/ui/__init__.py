"""UI package — Builder Pattern for tables, pure formatting helpers, and renderers."""

from dashboard.ui.formatters import format_number, format_pct, format_currency, make_sparkline
from dashboard.ui.builders import TableBuilder
from dashboard.ui.renderers import (
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
)

__all__ = [
    # Formatters
    "format_number",
    "format_pct",
    "format_currency",
    "make_sparkline",
    # Builder
    "TableBuilder",
    # Renderers
    "render_header",
    "render_description",
    "render_ratios",
    "render_price_history",
    "render_financials",
    "render_news",
    "render_analyst_recommendations",
    "render_major_holders",
    "render_comparison",
    "render_watchlist",
    "export_to_html",
    "render_detailed_financials",
    "render_sec_filings",
    "render_insider_transactions",
    "render_india_fund_overview",
    "render_fund_returns",
    "render_india_fund_search_results",
    "render_global_fund_snapshot",
    "render_global_fund_detail",
]
