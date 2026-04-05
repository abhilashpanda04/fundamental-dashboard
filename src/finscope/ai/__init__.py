"""AI-powered analysis module for finscope.

Provides LLM-driven financial analysis using pydantic-ai.  All features
are **opt-in** — they only activate when a provider API key is set in the
environment.

Supported providers (via pydantic-ai):
    - OpenAI        → OPENAI_API_KEY
    - Anthropic     → ANTHROPIC_API_KEY
    - Google Gemini → GEMINI_API_KEY
    - Groq          → GROQ_API_KEY
    - Mistral       → MISTRAL_API_KEY

Quick start::

    export OPENAI_API_KEY=sk-...

    import finscope
    aapl = finscope.stock("AAPL")

    # Structured analysis
    analysis = await aapl.analyze()
    print(analysis.summary)
    print(analysis.bull_case)
    print(analysis.bear_case)

    # Ask anything
    answer = await aapl.ask("Is AAPL overvalued compared to its peers?")
    print(answer)

    # AI-powered comparison
    insight = await finscope.ai_compare("AAPL", "MSFT", "GOOGL")
    print(insight)
"""

from finscope.ai.config import get_ai_model, is_ai_available, get_ai_status
from finscope.ai.models import StockAnalysis, ComparisonInsight, FilingSummary
from finscope.ai.agents import (
    analyze_stock,
    ask_stock,
    ai_compare_stocks,
    summarize_filings,
)

__all__ = [
    # Config
    "get_ai_model",
    "is_ai_available",
    "get_ai_status",
    # Output models
    "StockAnalysis",
    "ComparisonInsight",
    "FilingSummary",
    # Agent functions
    "analyze_stock",
    "ask_stock",
    "ai_compare_stocks",
    "summarize_filings",
]
