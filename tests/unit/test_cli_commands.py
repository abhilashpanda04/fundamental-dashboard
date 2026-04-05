"""Unit tests for CLI — direct commands + interactive mode + command registry."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from finscope.cli import (
    BalanceSheetCommand,
    CashFlowCommand,
    ChangeTickerCommand,
    CommandRegistry,
    DashboardCommand,
    DashboardContext,
    IncomeStatementCommand,
    KeyRatiosCommand,
    NewsCommand,
    OverviewCommand,
    _build_registry,
    _dispatch,
    _build_parser,
    cmd_overview,
    cmd_ratios,
    cmd_price,
    cmd_financials,
    cmd_news,
    cmd_compare,
    cmd_watchlist,
    cmd_export,
)
from finscope.services import FundAnalysisService
from finscope.stock import Stock


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_stock(apple_info, sample_price_df, sample_financials_df, sample_news):
    mock_svc = MagicMock()
    mock_svc.get_info.return_value = apple_info
    mock_svc.get_key_ratios.return_value = MagicMock(
        to_display_dict=lambda: {"P/E Ratio": 28.5, "Beta": 1.29}
    )
    mock_svc.get_sparkline.return_value = [100.0, 110.0]
    mock_svc.get_news.return_value = sample_news
    mock_svc.get_financials.return_value = sample_financials_df
    mock_svc.get_balance_sheet.return_value = sample_financials_df
    mock_svc.get_cashflow.return_value = sample_financials_df
    return Stock("AAPL", service=mock_svc)


@pytest.fixture
def ctx(mock_stock):
    return DashboardContext(stock=mock_stock, fund_service=MagicMock(spec=FundAnalysisService))


# ── Parser tests ──────────────────────────────────────────────────────────────

class TestParser:
    def test_parse_ticker_only(self):
        parser = _build_parser()
        ns = parser.parse_args(["AAPL"])
        assert ns.args == ["AAPL"]
        assert ns.interactive is False

    def test_parse_ticker_with_subcommand(self):
        parser = _build_parser()
        ns = parser.parse_args(["AAPL", "ratios"])
        assert ns.args == ["AAPL", "ratios"]

    def test_parse_interactive_flag(self):
        parser = _build_parser()
        ns = parser.parse_args(["AAPL", "-i"])
        assert ns.interactive is True

    def test_parse_compare(self):
        parser = _build_parser()
        ns = parser.parse_args(["compare", "AAPL", "MSFT", "GOOGL"])
        assert ns.args == ["compare", "AAPL", "MSFT", "GOOGL"]

    def test_parse_export_with_output(self):
        parser = _build_parser()
        ns = parser.parse_args(["export", "AAPL", "-o", "report.html"])
        assert ns.args == ["export", "AAPL"]
        assert ns.output == "report.html"

    def test_parse_price_with_period(self):
        parser = _build_parser()
        ns = parser.parse_args(["AAPL", "price", "1y"])
        assert ns.args == ["AAPL", "price", "1y"]

    def test_parse_sec_financials_with_category(self):
        parser = _build_parser()
        ns = parser.parse_args(["AAPL", "sec-financials", "--category", "cashflow"])
        assert ns.category == "cashflow"

    def test_parse_no_args(self):
        parser = _build_parser()
        ns = parser.parse_args([])
        assert ns.args == []

    def test_parse_funds(self):
        parser = _build_parser()
        ns = parser.parse_args(["funds"])
        assert ns.args == ["funds"]

    def test_parse_watchlist(self):
        parser = _build_parser()
        ns = parser.parse_args(["watchlist", "AAPL", "TSLA", "NVDA"])
        assert ns.args == ["watchlist", "AAPL", "TSLA", "NVDA"]


# ── Dispatch tests ────────────────────────────────────────────────────────────

class TestDispatch:
    def test_no_args_prints_banner(self):
        parser = _build_parser()
        ns = parser.parse_args([])
        with patch("finscope.cli._print_banner") as mock_banner, \
             patch("finscope.cli.console"):
            _dispatch(ns)
        mock_banner.assert_called_once()

    def test_ticker_only_calls_overview(self):
        parser = _build_parser()
        ns = parser.parse_args(["AAPL"])
        with patch("finscope.cli.cmd_overview") as mock_cmd:
            _dispatch(ns)
        mock_cmd.assert_called_once_with("AAPL")

    def test_ticker_with_ratios(self):
        parser = _build_parser()
        ns = parser.parse_args(["AAPL", "ratios"])
        with patch("finscope.cli.cmd_ratios") as mock_cmd:
            _dispatch(ns)
        mock_cmd.assert_called_once_with("AAPL")

    def test_ticker_with_price_and_period_arg(self):
        parser = _build_parser()
        ns = parser.parse_args(["AAPL", "price", "1y"])
        with patch("finscope.cli.cmd_price") as mock_cmd:
            _dispatch(ns)
        mock_cmd.assert_called_once_with("AAPL", "1y")

    def test_ticker_with_price_default_period(self):
        parser = _build_parser()
        ns = parser.parse_args(["AAPL", "price"])
        with patch("finscope.cli.cmd_price") as mock_cmd:
            _dispatch(ns)
        mock_cmd.assert_called_once_with("AAPL", "1mo")

    def test_compare_dispatches(self):
        parser = _build_parser()
        ns = parser.parse_args(["compare", "AAPL", "MSFT"])
        with patch("finscope.cli.cmd_compare") as mock_cmd:
            _dispatch(ns)
        mock_cmd.assert_called_once_with(["AAPL", "MSFT"])

    def test_watchlist_dispatches(self):
        parser = _build_parser()
        ns = parser.parse_args(["watchlist", "AAPL", "TSLA"])
        with patch("finscope.cli.cmd_watchlist") as mock_cmd:
            _dispatch(ns)
        mock_cmd.assert_called_once_with(["AAPL", "TSLA"])

    def test_export_dispatches(self):
        parser = _build_parser()
        ns = parser.parse_args(["export", "AAPL", "-o", "out.html"])
        with patch("finscope.cli.cmd_export") as mock_cmd:
            _dispatch(ns)
        mock_cmd.assert_called_once_with("AAPL", output="out.html")

    def test_funds_dispatches(self):
        parser = _build_parser()
        ns = parser.parse_args(["funds"])
        with patch("finscope.cli._print_banner"), \
             patch("finscope.cli._run_mutual_funds_menu") as mock_mf:
            _dispatch(ns)
        mock_mf.assert_called_once()

    def test_unknown_subcommand_prints_error(self):
        parser = _build_parser()
        ns = parser.parse_args(["AAPL", "garbage"])
        with patch("finscope.cli.console") as mock_console:
            _dispatch(ns)
        calls = [str(c) for c in mock_console.print.call_args_list]
        assert any("Unknown command" in c for c in calls)

    def test_interactive_flag_calls_run_interactive(self):
        parser = _build_parser()
        ns = parser.parse_args(["AAPL", "-i"])
        with patch("finscope.cli._print_banner"), \
             patch("finscope.cli.run_interactive", return_value=False) as mock_run:
            _dispatch(ns)
        mock_run.assert_called_once_with("AAPL")

    def test_all_subcommands_dispatch(self):
        """Every valid subcommand should route to a cmd_ function."""
        subcommands = {
            "overview": "cmd_overview",
            "ratios": "cmd_ratios",
            "price": "cmd_price",
            "financials": "cmd_financials",
            "balance-sheet": "cmd_balance_sheet",
            "cashflow": "cmd_cashflow",
            "news": "cmd_news",
            "analysts": "cmd_analysts",
            "holders": "cmd_holders",
            "sec-financials": "cmd_sec_financials",
            "sec-filings": "cmd_sec_filings",
            "insiders": "cmd_insiders",
        }
        for sub, func_name in subcommands.items():
            parser = _build_parser()
            ns = parser.parse_args(["AAPL", sub])
            with patch(f"finscope.cli.{func_name}") as mock_cmd:
                _dispatch(ns)
            assert mock_cmd.called, f"{func_name} not called for subcommand '{sub}'"


# ── Direct command tests ──────────────────────────────────────────────────────

class TestDirectCommands:
    def test_cmd_compare_needs_2_tickers(self):
        with patch("finscope.cli.console") as mock_console:
            cmd_compare(["AAPL"])
        calls = [str(c) for c in mock_console.print.call_args_list]
        assert any("at least 2" in c for c in calls)

    def test_cmd_watchlist_needs_1_ticker(self):
        with patch("finscope.cli.console") as mock_console:
            cmd_watchlist([])
        calls = [str(c) for c in mock_console.print.call_args_list]
        assert any("at least 1" in c for c in calls)

    def test_cmd_export_missing_ticker(self):
        parser = _build_parser()
        ns = parser.parse_args(["export"])
        with patch("finscope.cli.console") as mock_console:
            _dispatch(ns)
        calls = [str(c) for c in mock_console.print.call_args_list]
        assert any("Usage" in c for c in calls)


# ── DashboardContext tests ────────────────────────────────────────────────────

class TestDashboardContext:
    def test_symbol_delegates_to_stock(self, ctx):
        assert ctx.symbol == "AAPL"

    def test_info_delegates_to_stock(self, ctx):
        assert ctx.info["symbol"] == "AAPL"

    def test_sparkline_delegates_to_stock(self, ctx):
        assert ctx.sparkline == [100.0, 110.0]


# ── Command Registry tests ───────────────────────────────────────────────────

class TestCommandRegistry:
    def test_register_and_get(self):
        reg = CommandRegistry()
        cmd = MagicMock()
        reg.register(1, "Test", cmd)
        assert reg.get(1) is cmd

    def test_get_returns_none_for_unknown_key(self):
        assert CommandRegistry().get(99) is None

    def test_label(self):
        reg = CommandRegistry()
        reg.register(1, "My Label", None)
        assert reg.label(1) == "My Label"

    def test_items(self):
        reg = CommandRegistry()
        reg.register(1, "A", None).register(2, "B", None)
        keys = [k for k, _ in reg.items()]
        assert keys == [1, 2]

    def test_method_chaining(self):
        reg = CommandRegistry()
        assert reg.register(1, "A", None) is reg


class TestBuildRegistry:
    def test_all_menu_items_registered(self):
        reg = _build_registry()
        for key in range(18):
            assert reg.label(key) != "", f"Key {key} not registered"

    def test_exit_is_none(self):
        assert _build_registry().get(0) is None

    def test_all_commands_are_concrete(self):
        reg = _build_registry()
        for key, label in reg.items():
            cmd = reg.get(key)
            if key != 0:
                assert isinstance(cmd, DashboardCommand), f"Key {key} not a command"


# ── Interactive command tests ─────────────────────────────────────────────────

class TestInteractiveCommands:
    def test_overview(self, ctx):
        with patch("finscope.cli.render_header") as h, \
             patch("finscope.cli.render_description") as d:
            OverviewCommand().execute(ctx)
        h.assert_called_once()
        d.assert_called_once()

    def test_key_ratios(self, ctx):
        with patch("finscope.cli.render_ratios") as r:
            KeyRatiosCommand().execute(ctx)
        r.assert_called_once()

    def test_news(self, ctx, sample_news):
        with patch("finscope.cli.render_news") as r:
            NewsCommand().execute(ctx)
        r.assert_called_once_with(sample_news)

    def test_income_statement(self, ctx, sample_financials_df):
        with patch("finscope.cli.render_financials") as r:
            IncomeStatementCommand().execute(ctx)
        r.assert_called_once_with(sample_financials_df, "Income Statement")

    def test_balance_sheet(self, ctx, sample_financials_df):
        with patch("finscope.cli.render_financials") as r:
            BalanceSheetCommand().execute(ctx)
        r.assert_called_once_with(sample_financials_df, "Balance Sheet")

    def test_cashflow(self, ctx, sample_financials_df):
        with patch("finscope.cli.render_financials") as r:
            CashFlowCommand().execute(ctx)
        r.assert_called_once_with(sample_financials_df, "Cash Flow Statement")

    def test_change_ticker_is_command(self):
        assert isinstance(ChangeTickerCommand(), DashboardCommand)
