"""Backward-compatible ui module.

All symbols are re-exported from the new ``finscope.ui`` package.

.. deprecated::
    Import from ``finscope.ui`` (the package) directly.
"""

from finscope.ui.formatters import make_sparkline as _make_sparkline  # noqa: F401
from finscope.ui.renderers import (  # noqa: F401
    export_to_html,
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
