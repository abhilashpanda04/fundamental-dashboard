"""Unit tests for CLI Command Pattern classes."""

from __future__ import annotations

from unittest.mock import MagicMock, patch, PropertyMock

import pandas as pd
import pytest

from finscope.cli import (
    BalanceSheetCommand,
    CashFlowCommand,
    ChangeTickerCommand,
    CommandRegistry,
    DashboardContext,
    IncomeStatementCommand,
    KeyRatiosCommand,
    NewsCommand,
    OverviewCommand,
    _build_registry,
)
from finscope.services import FundAnalysisService
from finscope.stock import Stock


@pytest.fixture
def mock_stock(apple_info, sample_price_df, sample_financials_df, sample_news):
    """Mock Stock object with pre-set cached properties."""
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

    s = Stock("AAPL", service=mock_svc)
    return s


@pytest.fixture
def mock_fund_service():
    return MagicMock(spec=FundAnalysisService)


@pytest.fixture
def ctx(mock_stock, mock_fund_service):
    return DashboardContext(stock=mock_stock, fund_service=mock_fund_service)


class TestDashboardContext:
    def test_symbol_delegates_to_stock(self, ctx):
        assert ctx.symbol == "AAPL"

    def test_info_delegates_to_stock(self, ctx, apple_info):
        assert ctx.info["symbol"] == "AAPL"

    def test_sparkline_delegates_to_stock(self, ctx):
        assert ctx.sparkline == [100.0, 110.0]


class TestCommandRegistry:
    def test_register_and_get(self):
        reg = CommandRegistry()
        cmd = MagicMock()
        reg.register(1, "Test", cmd)
        assert reg.get(1) is cmd

    def test_get_returns_none_for_unknown_key(self):
        reg = CommandRegistry()
        assert reg.get(99) is None

    def test_label_returns_correct_string(self):
        reg = CommandRegistry()
        reg.register(1, "My Label", None)
        assert reg.label(1) == "My Label"

    def test_items_returns_all_entries(self):
        reg = CommandRegistry()
        reg.register(1, "One", None)
        reg.register(2, "Two", None)
        keys = [k for k, _ in reg.items()]
        assert 1 in keys
        assert 2 in keys

    def test_method_chaining(self):
        reg = CommandRegistry()
        result = reg.register(1, "A", None).register(2, "B", None)
        assert result is reg


class TestBuildRegistry:
    def test_registry_has_all_menu_items(self):
        reg = _build_registry()
        for key in range(18):
            assert reg.label(key) != "", f"Missing label for key {key}"

    def test_exit_key_zero_has_none_command(self):
        reg = _build_registry()
        assert reg.get(0) is None


class TestOverviewCommand:
    def test_execute_calls_render_functions(self, ctx):
        cmd = OverviewCommand()
        with (
            patch("finscope.cli.render_header") as mock_header,
            patch("finscope.cli.render_description") as mock_desc,
        ):
            cmd.execute(ctx)
        mock_header.assert_called_once_with(ctx.info, ctx.sparkline)
        mock_desc.assert_called_once_with(ctx.info)


class TestKeyRatiosCommand:
    def test_execute_calls_render_ratios(self, ctx):
        cmd = KeyRatiosCommand()
        with patch("finscope.cli.render_ratios") as mock_render:
            cmd.execute(ctx)
        mock_render.assert_called_once()


class TestNewsCommand:
    def test_execute_fetches_and_renders_news(self, ctx, sample_news):
        cmd = NewsCommand()
        with patch("finscope.cli.render_news") as mock_render:
            cmd.execute(ctx)
        mock_render.assert_called_once_with(sample_news)


class TestIncomeStatementCommand:
    def test_execute(self, ctx, sample_financials_df):
        cmd = IncomeStatementCommand()
        with patch("finscope.cli.render_financials") as mock_render:
            cmd.execute(ctx)
        mock_render.assert_called_once_with(sample_financials_df, "Income Statement")


class TestBalanceSheetCommand:
    def test_execute(self, ctx, sample_financials_df):
        cmd = BalanceSheetCommand()
        with patch("finscope.cli.render_financials") as mock_render:
            cmd.execute(ctx)
        mock_render.assert_called_once_with(sample_financials_df, "Balance Sheet")


class TestCashFlowCommand:
    def test_execute(self, ctx, sample_financials_df):
        cmd = CashFlowCommand()
        with patch("finscope.cli.render_financials") as mock_render:
            cmd.execute(ctx)
        mock_render.assert_called_once_with(sample_financials_df, "Cash Flow Statement")


class TestChangeTickerCommand:
    def test_is_a_dashboard_command(self):
        from finscope.cli import DashboardCommand
        cmd = ChangeTickerCommand()
        assert isinstance(cmd, DashboardCommand)
