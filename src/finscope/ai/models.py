"""Structured output models for AI analysis.

These Pydantic models define the **shape** of every AI response.
pydantic-ai uses them to constrain LLM output, so callers always get
typed, predictable objects — never raw text.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

__all__ = ["StockAnalysis", "ComparisonInsight", "FilingSummary"]


class StockAnalysis(BaseModel):
    """Structured output from the stock analysis agent."""

    summary: str = Field(
        description="2-3 sentence executive summary of the stock's current position."
    )
    bull_case: list[str] = Field(
        description="3-5 bullet points supporting a bullish thesis."
    )
    bear_case: list[str] = Field(
        description="3-5 bullet points supporting a bearish thesis."
    )
    key_metrics_commentary: str = Field(
        description="Analysis of the most important financial ratios and what they imply."
    )
    financial_health: str = Field(
        description="Assessment of balance sheet strength, debt levels, and cash flow quality."
    )
    growth_outlook: str = Field(
        description="Forward-looking assessment of revenue and earnings growth potential."
    )
    risk_factors: list[str] = Field(
        description="2-4 key risks an investor should be aware of."
    )
    sentiment: str = Field(
        description="Overall sentiment: 'Bullish', 'Moderately Bullish', 'Neutral', 'Moderately Bearish', or 'Bearish'."
    )
    confidence: str = Field(
        description="Confidence level in this analysis: 'High', 'Medium', or 'Low', with a brief reason."
    )


class ComparisonInsight(BaseModel):
    """Structured output from the multi-stock comparison agent."""

    overview: str = Field(
        description="1-2 paragraph overview comparing all stocks holistically."
    )
    rankings: list[str] = Field(
        description="Stocks ranked by overall investment attractiveness with brief justification."
    )
    valuation_comparison: str = Field(
        description="Which stocks look cheap vs expensive and why."
    )
    growth_comparison: str = Field(
        description="Which stocks have stronger growth profiles and why."
    )
    risk_comparison: str = Field(
        description="Relative risk levels across the group."
    )
    best_for: dict[str, str] = Field(
        description="Best stock for different investor profiles, e.g. {'Value investor': 'AAPL because...', 'Growth investor': 'MSFT because...'}."
    )


class FilingSummary(BaseModel):
    """Structured output from the SEC filing summarizer agent."""

    company: str = Field(description="Company name and ticker.")
    filing_types_covered: list[str] = Field(
        description="List of filing types analyzed (e.g. ['10-K', '10-Q', '8-K'])."
    )
    key_highlights: list[str] = Field(
        description="5-8 most important takeaways from the recent filings."
    )
    risk_factors: list[str] = Field(
        description="Key risk factors disclosed in the filings."
    )
    management_outlook: str = Field(
        description="Summary of management's forward-looking statements and guidance."
    )
    notable_changes: list[str] = Field(
        description="Any notable changes from prior filings (accounting, strategy, leadership, etc.)."
    )
