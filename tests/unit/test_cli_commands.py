"""Unit tests for CLI Command Pattern classes."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from dashboard.cli import (
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
from dashboard.services import FundAnalysisService, StockAnalysisService


@pytest.fixture
def mock_stock_service(apple_info, sample_price_df, sample_news):
    m = MagicMock(spec=StockAnalysisService)
    m.get_info.return_value = apple_info
    m.get_key_ratios.return_value = MagicMock(
        to_display_dict=lambda: {"P/E Ratio": 28.5, "Beta": 1.29}
    )
    m.get_price_history.return_value = sample_price_df
    m.get_sparkline.return_value = [100.0, 110.0]
    m.get_news.return_value = sample_news
    m.get_financials.return_value = sample_price_df
    m.get_balance_sheet.return_value = sample_price_df
    m.get_cashflow.return_value = sample_price_df
    return m


@pytest.fixture
def mock_fund_service():
    return MagicMock(spec=FundAnalysisService)


@pytest.fixture
def ctx(apple_info, mock_stock_service, mock_fund_service):
    return DashboardContext(
        symbol="AAPL",
        info=apple_info,
        sparkline=[100.0, 110.0, 120.0],
        stock_service=mock_stock_service,
        fund_service=mock_fund_service,
    )


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
        # Verify key items are present
        for key in [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17]:
            assert reg.label(key) != "", f"Missing label for key {key}"

    def test_exit_key_zero_has_none_command(self):
        reg = _build_registry()
        assert reg.get(0) is None


class TestOverviewCommand:
    def test_execute_calls_render_functions(self, ctx):
        cmd = OverviewCommand()
        with (
            patch("dashboard.cli.render_header") as mock_header,
            patch("dashboard.cli.render_description") as mock_desc,
        ):
            cmd.execute(ctx)
        mock_header.assert_called_once_with(ctx.info, ctx.sparkline)
        mock_desc.assert_called_once_with(ctx.info)


class TestKeyRatiosCommand:
    def test_execute_calls_render_ratios(self, ctx, mock_stock_service):
        cmd = KeyRatiosCommand()
        with patch("dashboard.cli.render_ratios") as mock_render:
            cmd.execute(ctx)
        mock_render.assert_called_once()
        mock_stock_service.get_key_ratios.assert_called_once_with(ctx.info)


class TestNewsCommand:
    def test_execute_fetches_and_renders_news(self, ctx, mock_stock_service, sample_news):
        mock_stock_service.get_news.return_value = sample_news
        cmd = NewsCommand()
        with patch("dashboard.cli.render_news") as mock_render:
            cmd.execute(ctx)
        mock_stock_service.get_news.assert_called_once_with("AAPL")
        mock_render.assert_called_once_with(sample_news)


class TestIncomeStatementCommand:
    def test_execute_calls_render_financials(self, ctx, mock_stock_service, sample_price_df):
        cmd = IncomeStatementCommand()
        with patch("dashboard.cli.render_financials") as mock_render:
            cmd.execute(ctx)
        mock_render.assert_called_once_with(sample_price_df, "Income Statement")


class TestBalanceSheetCommand:
    def test_execute_calls_render_financials(self, ctx, mock_stock_service, sample_price_df):
        cmd = BalanceSheetCommand()
        with patch("dashboard.cli.render_financials") as mock_render:
            cmd.execute(ctx)
        mock_render.assert_called_once_with(sample_price_df, "Balance Sheet")


class TestCashFlowCommand:
    def test_execute_calls_render_financials(self, ctx, mock_stock_service, sample_price_df):
        cmd = CashFlowCommand()
        with patch("dashboard.cli.render_financials") as mock_render:
            cmd.execute(ctx)
        mock_render.assert_called_once_with(sample_price_df, "Cash Flow Statement")


class TestChangeTickerCommand:
    def test_is_a_dashboard_command(self):
        from dashboard.cli import DashboardCommand
        cmd = ChangeTickerCommand()
        assert isinstance(cmd, DashboardCommand)
