"""Unit tests for the finscope.ai module.

All LLM calls are mocked — no real API keys or network required.
"""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from finscope.ai.config import get_ai_model, get_ai_status, is_ai_available
from finscope.ai.models import ComparisonInsight, FilingSummary, StockAnalysis
from finscope.ai.tools import StockContext, _df_to_str, _format_ratios


# ── Config tests ──────────────────────────────────────────────────────────────


class TestAIConfig:
    def test_no_keys_returns_none(self, monkeypatch):
        for var in ["FINSCOPE_AI_MODEL", "OPENAI_API_KEY", "ANTHROPIC_API_KEY",
                     "GEMINI_API_KEY", "GROQ_API_KEY", "MISTRAL_API_KEY"]:
            monkeypatch.delenv(var, raising=False)
        assert get_ai_model() is None

    def test_not_available_without_keys(self, monkeypatch):
        for var in ["FINSCOPE_AI_MODEL", "OPENAI_API_KEY", "ANTHROPIC_API_KEY",
                     "GEMINI_API_KEY", "GROQ_API_KEY", "MISTRAL_API_KEY"]:
            monkeypatch.delenv(var, raising=False)
        assert is_ai_available() is False

    def test_openai_key_detected(self, monkeypatch):
        monkeypatch.delenv("FINSCOPE_AI_MODEL", raising=False)
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        assert get_ai_model() == "openai:gpt-4o"
        assert is_ai_available() is True

    def test_anthropic_key_detected(self, monkeypatch):
        for var in ["FINSCOPE_AI_MODEL", "OPENAI_API_KEY"]:
            monkeypatch.delenv(var, raising=False)
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
        assert "anthropic" in get_ai_model()

    def test_gemini_key_detected(self, monkeypatch):
        for var in ["FINSCOPE_AI_MODEL", "OPENAI_API_KEY", "ANTHROPIC_API_KEY"]:
            monkeypatch.delenv(var, raising=False)
        monkeypatch.setenv("GEMINI_API_KEY", "test")
        assert "google" in get_ai_model()

    def test_groq_key_detected(self, monkeypatch):
        for var in ["FINSCOPE_AI_MODEL", "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY"]:
            monkeypatch.delenv(var, raising=False)
        monkeypatch.setenv("GROQ_API_KEY", "gsk-test")
        assert "groq" in get_ai_model()

    def test_explicit_model_override(self, monkeypatch):
        monkeypatch.setenv("FINSCOPE_AI_MODEL", "openai:gpt-4o-mini")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
        # Explicit should take priority
        assert get_ai_model() == "openai:gpt-4o-mini"

    def test_priority_order(self, monkeypatch):
        monkeypatch.delenv("FINSCOPE_AI_MODEL", raising=False)
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
        # OpenAI should win
        assert get_ai_model() == "openai:gpt-4o"

    def test_status_unavailable(self, monkeypatch):
        for var in ["FINSCOPE_AI_MODEL", "OPENAI_API_KEY", "ANTHROPIC_API_KEY",
                     "GEMINI_API_KEY", "GROQ_API_KEY", "MISTRAL_API_KEY"]:
            monkeypatch.delenv(var, raising=False)
        status = get_ai_status()
        assert status["available"] is False
        assert status["model"] is None

    def test_status_available(self, monkeypatch):
        monkeypatch.delenv("FINSCOPE_AI_MODEL", raising=False)
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        status = get_ai_status()
        assert status["available"] is True
        assert status["model"] == "openai:gpt-4o"
        assert "OpenAI" in status["provider"]

    def test_status_explicit_model(self, monkeypatch):
        monkeypatch.setenv("FINSCOPE_AI_MODEL", "custom:model")
        status = get_ai_status()
        assert status["available"] is True
        assert "Custom" in status["provider"]


# ── Structured output model tests ─────────────────────────────────────────────


class TestAIModels:
    def test_stock_analysis_construction(self):
        analysis = StockAnalysis(
            summary="Apple is a tech giant.",
            bull_case=["Strong ecosystem", "Services growth"],
            bear_case=["China risk", "Regulation"],
            key_metrics_commentary="P/E of 28.5 is reasonable.",
            financial_health="Strong balance sheet.",
            growth_outlook="Moderate growth expected.",
            risk_factors=["Competition", "Supply chain"],
            sentiment="Moderately Bullish",
            confidence="Medium — limited forward visibility",
        )
        assert analysis.sentiment == "Moderately Bullish"
        assert len(analysis.bull_case) == 2
        assert len(analysis.risk_factors) == 2

    def test_comparison_insight_construction(self):
        insight = ComparisonInsight(
            overview="AAPL vs MSFT comparison.",
            rankings=["1. MSFT — stronger growth", "2. AAPL — better margins"],
            valuation_comparison="MSFT trades at a premium.",
            growth_comparison="MSFT has higher revenue growth.",
            risk_comparison="Both have similar risk profiles.",
            best_for={"Value investor": "AAPL", "Growth investor": "MSFT"},
        )
        assert len(insight.rankings) == 2
        assert "AAPL" in insight.best_for["Value investor"]

    def test_filing_summary_construction(self):
        summary = FilingSummary(
            company="Apple Inc. (AAPL)",
            filing_types_covered=["10-K", "10-Q"],
            key_highlights=["Revenue grew 5%", "Margins expanded"],
            risk_factors=["Geopolitical risk"],
            management_outlook="Cautiously optimistic.",
            notable_changes=["New accounting standard adopted"],
        )
        assert "10-K" in summary.filing_types_covered
        assert len(summary.key_highlights) == 2


# ── Tools tests ───────────────────────────────────────────────────────────────


class TestStockContext:
    def test_symbol_stored(self):
        ctx = StockContext(symbol="AAPL")
        assert ctx.symbol == "AAPL"

    def test_stock_lazy_loaded(self):
        ctx = StockContext(symbol="AAPL")
        assert ctx._stock is None  # Not loaded yet

    def test_extra_symbols(self):
        ctx = StockContext(symbol="AAPL", _extra_symbols=["MSFT", "GOOGL"])
        assert ctx._extra_symbols == ["MSFT", "GOOGL"]


class TestToolHelpers:
    def test_df_to_str_with_none(self):
        assert _df_to_str(None) == "No data available."

    def test_df_to_str_with_data(self, sample_price_df):
        result = _df_to_str(sample_price_df)
        assert "Open" in result or "Close" in result

    def test_format_ratios_with_data(self):
        ratios = {"P/E Ratio": 28.5, "Beta": 1.29, "Market Cap": 2_700_000_000_000}
        result = _format_ratios(ratios)
        assert "P/E Ratio" in result
        assert "28.50" in result

    def test_format_ratios_empty(self):
        result = _format_ratios({})
        assert "No ratio data" in result

    def test_format_ratios_none_values_skipped(self):
        ratios = {"P/E Ratio": None, "Beta": 1.0}
        result = _format_ratios(ratios)
        assert "P/E Ratio" not in result
        assert "Beta" in result

    def test_format_ratios_billions(self):
        result = _format_ratios({"Market Cap": 2_500_000_000_000})
        assert "B" in result

    def test_format_ratios_millions(self):
        result = _format_ratios({"Revenue": 394_000_000})
        assert "M" in result


# ── Agent function tests (mocked) ─────────────────────────────────────────────


class TestAgentFunctions:
    def test_ai_not_available_error(self, monkeypatch):
        for var in ["FINSCOPE_AI_MODEL", "OPENAI_API_KEY", "ANTHROPIC_API_KEY",
                     "GEMINI_API_KEY", "GROQ_API_KEY", "MISTRAL_API_KEY"]:
            monkeypatch.delenv(var, raising=False)

        from finscope.ai.agents import AINotAvailableError, _require_model
        with pytest.raises(AINotAvailableError):
            _require_model()

    def test_ai_not_available_inherits_finscope_error(self):
        from finscope.ai.agents import AINotAvailableError
        from finscope.exceptions import FinScopeError
        assert issubclass(AINotAvailableError, FinScopeError)


# ── CLI AI command tests ──────────────────────────────────────────────────────


class TestCLIAICommands:
    def test_analyze_dispatch(self):
        from finscope.cli import _build_parser, _dispatch
        ns = _build_parser().parse_args(["AAPL", "analyze"])
        with patch("finscope.cli.cmd_analyze") as mock:
            _dispatch(ns)
        mock.assert_called_once_with("AAPL")

    def test_ask_dispatch(self):
        from finscope.cli import _build_parser, _dispatch
        ns = _build_parser().parse_args(["AAPL", "ask", "Is", "it", "overvalued?"])
        with patch("finscope.cli.cmd_ask") as mock:
            _dispatch(ns)
        mock.assert_called_once_with("AAPL", "Is it overvalued?")

    def test_summarize_filings_dispatch(self):
        from finscope.cli import _build_parser, _dispatch
        ns = _build_parser().parse_args(["AAPL", "summarize-filings"])
        with patch("finscope.cli.cmd_summarize_filings") as mock:
            _dispatch(ns)
        mock.assert_called_once_with("AAPL")

    def test_compare_analyze_dispatch(self):
        from finscope.cli import _build_parser, _dispatch
        ns = _build_parser().parse_args(["compare", "AAPL", "MSFT", "--analyze"])
        with patch("finscope.cli.cmd_ai_compare") as mock:
            _dispatch(ns)
        mock.assert_called_once_with(["AAPL", "MSFT"])

    def test_compare_without_analyze_uses_regular(self):
        from finscope.cli import _build_parser, _dispatch
        ns = _build_parser().parse_args(["compare", "AAPL", "MSFT"])
        with patch("finscope.cli.cmd_compare") as mock:
            _dispatch(ns)
        mock.assert_called_once_with(["AAPL", "MSFT"])

    def test_require_ai_exits_when_unavailable(self, monkeypatch):
        for var in ["FINSCOPE_AI_MODEL", "OPENAI_API_KEY", "ANTHROPIC_API_KEY",
                     "GEMINI_API_KEY", "GROQ_API_KEY", "MISTRAL_API_KEY"]:
            monkeypatch.delenv(var, raising=False)

        from finscope.cli import _require_ai
        with patch("finscope.cli.console"), pytest.raises(SystemExit):
            _require_ai()
