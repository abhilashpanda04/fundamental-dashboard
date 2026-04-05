"""pydantic-ai agent definitions for financial analysis.

Each agent has:
- A system prompt tailored to its analysis type
- Tools that give it access to finscope data
- A structured output model so responses are always typed

The agent decides which tools to call based on the user's question.
"""

from __future__ import annotations

from pydantic_ai import Agent

from finscope.ai.config import get_ai_model
from finscope.ai.models import ComparisonInsight, FilingSummary, StockAnalysis
from finscope.ai.prompt_loader import load_prompt
from finscope.ai.tools import (
    StockContext,
    register_comparison_tools,
    register_stock_tools,
)
from finscope.exceptions import FinScopeError

__all__ = [
    "analyze_stock",
    "ask_stock",
    "ai_compare_stocks",
    "summarize_filings",
]


class AINotAvailableError(FinScopeError):
    """Raised when AI features are used without a configured provider."""

    def __init__(self) -> None:
        super().__init__(
            "No AI provider configured. Set an API key environment variable:\n"
            "  export OPENAI_API_KEY=sk-...\n"
            "  export ANTHROPIC_API_KEY=sk-ant-...\n"
            "  export GEMINI_API_KEY=...\n"
            "  export GROQ_API_KEY=gsk_...\n"
            "  export MISTRAL_API_KEY=...\n"
            "Or set FINSCOPE_AI_MODEL explicitly."
        )


def _require_model() -> str:
    """Return the model string or raise if no provider is configured."""
    model = get_ai_model()
    if model is None:
        raise AINotAvailableError()
    return model


# ── Agent factory functions ───────────────────────────────────────────────────

def _build_analyst_agent() -> Agent[StockContext, StockAnalysis]:
    """Build the stock analysis agent with all data tools."""
    model = _require_model()
    agent = Agent(
        model,
        deps_type=StockContext,
        result_type=StockAnalysis,
        system_prompt=load_prompt("analyst"),
    )
    register_stock_tools(agent)
    return agent


def _build_qa_agent() -> Agent[StockContext, str]:
    """Build the conversational Q&A agent."""
    model = _require_model()
    agent = Agent(
        model,
        deps_type=StockContext,
        result_type=str,
        system_prompt=load_prompt("qa"),
    )
    register_stock_tools(agent)
    return agent


def _build_comparison_agent() -> Agent[StockContext, ComparisonInsight]:
    """Build the multi-stock comparison agent."""
    model = _require_model()
    agent = Agent(
        model,
        deps_type=StockContext,
        result_type=ComparisonInsight,
        system_prompt=load_prompt("comparison"),
    )
    register_stock_tools(agent)
    register_comparison_tools(agent)
    return agent


def _build_filing_agent() -> Agent[StockContext, FilingSummary]:
    """Build the SEC filing summarizer agent."""
    model = _require_model()
    agent = Agent(
        model,
        deps_type=StockContext,
        result_type=FilingSummary,
        system_prompt=load_prompt("filing"),
    )
    register_stock_tools(agent)
    return agent


# ── Public API ────────────────────────────────────────────────────────────────


async def analyze_stock(symbol: str) -> StockAnalysis:
    """Run a comprehensive AI analysis of a stock.

    The agent will autonomously call tools to fetch ratios, financials,
    price history, news, and analyst recommendations, then produce a
    structured analysis.

    Args:
        symbol: Ticker symbol (e.g. ``"AAPL"``).

    Returns:
        A :class:`StockAnalysis` with summary, bull/bear cases, and more.

    Raises:
        AINotAvailableError: If no LLM provider is configured.
        TickerNotFoundError: If the symbol is invalid.

    Example::

        analysis = await finscope.ai.analyze_stock("AAPL")
        print(analysis.summary)
        for point in analysis.bull_case:
            print(f"  + {point}")
    """
    agent = _build_analyst_agent()
    ctx = StockContext(symbol=symbol.upper())
    result = await agent.run(
        f"Perform a comprehensive fundamental analysis of {symbol.upper()}. "
        f"Fetch all relevant data using your tools, then provide your analysis.",
        deps=ctx,
    )
    return result.data


async def ask_stock(symbol: str, question: str) -> str:
    """Ask any question about a stock — the agent fetches data as needed.

    Args:
        symbol:   Ticker symbol.
        question: Natural language question.

    Returns:
        The agent's response as a string.

    Example::

        answer = await finscope.ai.ask_stock("TSLA", "What's Tesla's debt situation?")
        print(answer)
    """
    agent = _build_qa_agent()
    ctx = StockContext(symbol=symbol.upper())
    result = await agent.run(
        f"Regarding {symbol.upper()}: {question}",
        deps=ctx,
    )
    return result.data


async def ai_compare_stocks(*symbols: str) -> ComparisonInsight:
    """AI-powered comparison of multiple stocks.

    The agent fetches data for all tickers and produces a structured
    comparative analysis.

    Args:
        *symbols: Two or more ticker symbols.

    Returns:
        A :class:`ComparisonInsight` with rankings, comparisons, and recommendations.

    Example::

        insight = await finscope.ai.ai_compare_stocks("AAPL", "MSFT", "GOOGL")
        print(insight.overview)
        for rank in insight.rankings:
            print(f"  {rank}")
    """
    if len(symbols) < 2:
        raise ValueError("At least 2 symbols are required for comparison.")

    agent = _build_comparison_agent()
    primary = symbols[0].upper()
    extras = [s.upper() for s in symbols[1:]]
    ctx = StockContext(symbol=primary, _extra_symbols=extras)

    symbols_str = ", ".join(s.upper() for s in symbols)
    result = await agent.run(
        f"Compare these stocks: {symbols_str}. "
        f"Fetch the comparison data and individual details, then provide your analysis.",
        deps=ctx,
    )
    return result.data


async def summarize_filings(symbol: str) -> FilingSummary:
    """Summarize recent SEC filings for a stock.

    The agent reads SEC EDGAR data (XBRL financials, recent filings,
    insider transactions) and produces a structured summary.

    Args:
        symbol: Ticker symbol.

    Returns:
        A :class:`FilingSummary` with highlights, risks, and management outlook.

    Example::

        summary = await finscope.ai.summarize_filings("AAPL")
        for highlight in summary.key_highlights:
            print(f"  • {highlight}")
    """
    agent = _build_filing_agent()
    ctx = StockContext(symbol=symbol.upper())
    result = await agent.run(
        f"Analyze the recent SEC filings for {symbol.upper()}. "
        f"Fetch the SEC EDGAR data, recent filings list, and insider transactions, "
        f"then provide your summary.",
        deps=ctx,
    )
    return result.data
