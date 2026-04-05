"""Tools that expose finscope data to pydantic-ai agents.

Each tool is a plain function that the agent can call during reasoning.
Tools receive a ``RunContext[StockContext]`` and use it to pull data
from the underlying ``finscope.Stock`` object.

The agent decides *which* tools to call based on the user's question —
this is the key advantage over pre-fetching everything up front.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd
from pydantic_ai import RunContext

__all__ = ["StockContext", "register_stock_tools", "register_comparison_tools"]


@dataclass
class StockContext:
    """Runtime context passed to every tool call.

    Wraps one or more ``finscope.Stock`` objects so tools can lazily
    pull whatever data the agent requests.
    """

    symbol: str
    _stock: Any = field(repr=False, default=None)
    _extra_symbols: list[str] = field(default_factory=list)

    @property
    def stock(self):
        if self._stock is None:
            import finscope
            self._stock = finscope.stock(self.symbol)
        return self._stock


def _df_to_str(df: pd.DataFrame | None, max_rows: int = 10) -> str:
    """Convert a DataFrame to a compact string for the LLM context."""
    if df is None or (hasattr(df, "empty") and df.empty):
        return "No data available."
    return df.head(max_rows).to_string()


def _format_ratios(ratios_dict: dict) -> str:
    """Format ratios dict as a readable string."""
    lines = []
    for key, val in ratios_dict.items():
        if val is not None:
            if isinstance(val, (int, float)):
                v = float(val)
                if abs(v) >= 1_000_000_000:
                    lines.append(f"  {key}: ${v/1e9:.2f}B")
                elif abs(v) >= 1_000_000:
                    lines.append(f"  {key}: ${v/1e6:.2f}M")
                elif abs(v) < 1:
                    lines.append(f"  {key}: {v:.4f}")
                else:
                    lines.append(f"  {key}: {v:.2f}")
            else:
                lines.append(f"  {key}: {val}")
    return "\n".join(lines) if lines else "No ratio data available."


# ── Tool registration functions ───────────────────────────────────────────────


def register_stock_tools(agent) -> None:
    """Register all single-stock data tools on the given pydantic-ai agent."""

    @agent.tool
    def get_company_info(ctx: RunContext[StockContext]) -> str:
        """Get company overview: name, sector, industry, price, market cap, description."""
        info = ctx.deps.stock.info
        return (
            f"Company: {info.get('longName', 'N/A')} ({info.get('symbol', '')})\n"
            f"Sector: {info.get('sector', 'N/A')} / {info.get('industry', 'N/A')}\n"
            f"Exchange: {info.get('exchange', 'N/A')} | Currency: {info.get('currency', 'USD')}\n"
            f"Current Price: {info.get('currentPrice') or info.get('regularMarketPrice', 'N/A')}\n"
            f"Market Cap: {info.get('marketCap', 'N/A')}\n"
            f"52W High: {info.get('fiftyTwoWeekHigh', 'N/A')} | 52W Low: {info.get('fiftyTwoWeekLow', 'N/A')}\n"
            f"Description: {info.get('longBusinessSummary', 'N/A')[:500]}"
        )

    @agent.tool
    def get_key_ratios(ctx: RunContext[StockContext]) -> str:
        """Get all key financial ratios: P/E, P/B, P/S, EV/EBITDA, margins, ROE, debt/equity, beta, etc."""
        ratios = ctx.deps.stock.ratios.to_display_dict()
        return f"Key Financial Ratios for {ctx.deps.symbol}:\n{_format_ratios(ratios)}"

    @agent.tool
    def get_income_statement(ctx: RunContext[StockContext]) -> str:
        """Get the annual income statement (revenue, gross profit, net income, etc.)."""
        return f"Income Statement:\n{_df_to_str(ctx.deps.stock.financials, max_rows=15)}"

    @agent.tool
    def get_balance_sheet(ctx: RunContext[StockContext]) -> str:
        """Get the annual balance sheet (assets, liabilities, equity)."""
        return f"Balance Sheet:\n{_df_to_str(ctx.deps.stock.balance_sheet, max_rows=15)}"

    @agent.tool
    def get_cashflow_statement(ctx: RunContext[StockContext]) -> str:
        """Get the annual cash flow statement (operating, investing, financing cash flows)."""
        return f"Cash Flow Statement:\n{_df_to_str(ctx.deps.stock.cashflow, max_rows=15)}"

    @agent.tool
    def get_price_history(ctx: RunContext[StockContext], period: str = "3mo") -> str:
        """Get recent price history (OHLCV). Use period like '1mo', '3mo', '6mo', '1y'."""
        df = ctx.deps.stock.price_history(period)
        return f"Price History ({period}):\n{_df_to_str(df)}"

    @agent.tool
    def get_recent_news(ctx: RunContext[StockContext]) -> str:
        """Get recent news headlines for the stock."""
        news = ctx.deps.stock.news
        if not news:
            return "No recent news available."
        lines = []
        for i, article in enumerate(news[:8], 1):
            title = article.get("title") or article.get("content", {}).get("title", "No title")
            publisher = article.get("publisher") or article.get("content", {}).get("provider", {}).get("displayName", "Unknown")
            lines.append(f"  {i}. {title} — {publisher}")
        return f"Recent News:\n" + "\n".join(lines)

    @agent.tool
    def get_analyst_recommendations(ctx: RunContext[StockContext]) -> str:
        """Get analyst buy/sell/hold recommendation counts."""
        recs = ctx.deps.stock.analyst_recommendations
        if recs is None or recs.empty:
            return "No analyst recommendations available."
        latest = recs.iloc[0]
        return (
            f"Analyst Recommendations:\n"
            f"  Strong Buy: {latest.get('strongBuy', 0)}\n"
            f"  Buy: {latest.get('buy', 0)}\n"
            f"  Hold: {latest.get('hold', 0)}\n"
            f"  Sell: {latest.get('sell', 0)}\n"
            f"  Strong Sell: {latest.get('strongSell', 0)}"
        )

    @agent.tool
    def get_sec_financials(ctx: RunContext[StockContext], category: str = "Income Statement") -> str:
        """Get detailed XBRL financial data from SEC EDGAR. Categories: 'Income Statement', 'Balance Sheet (Assets)', 'Balance Sheet (Liabilities & Equity)', 'Cash Flow', 'Per Share & Shares', 'Debt Maturity Schedule'."""
        data = ctx.deps.stock.sec_financials
        if not data:
            return "No SEC EDGAR data available."
        cat_data = data.get(category, {})
        if not cat_data:
            available = ", ".join(data.keys())
            return f"Category '{category}' not found. Available: {available}"
        lines = [f"SEC EDGAR — {category}:"]
        for concept, values in cat_data.items():
            recent = values[-3:] if len(values) > 3 else values
            vals_str = ", ".join(
                f"FY{e.get('fy', '?')}: {e.get('val', 'N/A')}" for e in recent
            )
            lines.append(f"  {concept}: {vals_str}")
        return "\n".join(lines)

    @agent.tool
    def get_insider_transactions(ctx: RunContext[StockContext]) -> str:
        """Get recent insider transactions (Form 3/4/5 filings)."""
        txns = ctx.deps.stock.insider_transactions
        if not txns:
            return "No insider transactions found."
        lines = [f"Recent Insider Transactions ({len(txns)} filings):"]
        for t in txns[:10]:
            lines.append(f"  {t['date']} | {t['form']} | {t.get('description', 'N/A')[:60]}")
        return "\n".join(lines)

    @agent.tool
    def get_major_holders(ctx: RunContext[StockContext]) -> str:
        """Get ownership breakdown and top institutional holders."""
        breakdown, institutional = ctx.deps.stock.holders
        parts = []
        if breakdown is not None and not breakdown.empty:
            parts.append(f"Ownership Breakdown:\n{_df_to_str(breakdown)}")
        if institutional is not None and not institutional.empty:
            parts.append(f"\nTop Institutional Holders:\n{_df_to_str(institutional)}")
        return "\n".join(parts) if parts else "No holder data available."


def register_comparison_tools(agent) -> None:
    """Register tools for multi-stock comparison analysis."""

    @agent.tool
    def get_comparison_data(ctx: RunContext[StockContext]) -> str:
        """Get side-by-side comparison metrics for all stocks being compared."""
        import finscope

        all_symbols = [ctx.deps.symbol] + ctx.deps._extra_symbols
        data = finscope.compare(*all_symbols)
        if not data:
            return "No comparison data available."

        lines = ["Side-by-Side Comparison:"]
        for d in data:
            lines.append(f"\n  === {d.symbol} ({d.name}) ===")
            lines.append(f"  Price: {d.price}")
            lines.append(f"  Market Cap: {d.market_cap}")
            lines.append(f"  P/E: {d.pe_ratio}  |  Forward P/E: {d.forward_pe}  |  PEG: {d.peg}")
            lines.append(f"  P/B: {d.pb}  |  P/S: {d.ps}")
            if d.profit_margin is not None:
                lines.append(f"  Profit Margin: {d.profit_margin*100:.1f}%")
            if d.roe is not None:
                lines.append(f"  ROE: {d.roe*100:.1f}%")
            lines.append(f"  Debt/Equity: {d.debt_equity}  |  Beta: {d.beta}")
            lines.append(f"  Revenue: {d.revenue}  |  EBITDA: {d.ebitda}")
            if d.dividend_yield is not None:
                lines.append(f"  Dividend Yield: {d.dividend_yield*100:.2f}%")
        return "\n".join(lines)

    @agent.tool
    def get_stock_info(ctx: RunContext[StockContext], symbol: str) -> str:
        """Get detailed info for a specific stock in the comparison. Pass the ticker symbol."""
        import finscope

        s = finscope.stock(symbol)
        info = s.info
        ratios = s.ratios.to_display_dict()
        return (
            f"{info.get('longName', symbol)} ({symbol})\n"
            f"Sector: {info.get('sector', 'N/A')} / {info.get('industry', 'N/A')}\n"
            f"Description: {info.get('longBusinessSummary', 'N/A')[:300]}\n\n"
            f"Key Ratios:\n{_format_ratios(ratios)}"
        )
