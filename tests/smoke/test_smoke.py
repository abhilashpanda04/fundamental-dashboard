"""Smoke tests — verify the system starts up and core wiring is intact.

Smoke tests are intentionally lightweight: they check that modules import,
objects can be constructed, config is accessible, and the top-level entry
point can be invoked without crashing — all with no real network calls.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


# ── Import smoke tests ────────────────────────────────────────────────────────

class TestImports:
    """Every module must be importable without errors."""

    def test_import_top_level(self):
        import finscope  # noqa: F401

    def test_import_exceptions(self):
        import finscope.exceptions  # noqa: F401

    def test_import_config(self):
        import finscope.config  # noqa: F401

    def test_import_models(self):
        import finscope.models  # noqa: F401

    def test_import_stock(self):
        import finscope.stock  # noqa: F401

    def test_import_providers_base(self):
        import finscope.providers.base  # noqa: F401

    def test_import_yahoo_provider(self):
        import finscope.providers.yahoo_provider  # noqa: F401

    def test_import_sec_edgar_provider(self):
        import finscope.providers.sec_edgar_provider  # noqa: F401

    def test_import_mfapi_provider(self):
        import finscope.providers.mfapi_provider  # noqa: F401

    def test_import_services_stock(self):
        import finscope.services.stock_service  # noqa: F401

    def test_import_services_fund(self):
        import finscope.services.fund_service  # noqa: F401

    def test_import_ui_formatters(self):
        import finscope.ui.formatters  # noqa: F401

    def test_import_ui_builders(self):
        import finscope.ui.builders  # noqa: F401

    def test_import_ui_renderers(self):
        import finscope.ui.renderers  # noqa: F401

    def test_import_cli(self):
        import finscope.cli  # noqa: F401

    # Backward-compat modules (removed — these were shims)
    # If you need the old imports, use the new paths:
    #   finscope.data          → finscope.providers.yahoo_provider
    #   finscope.sec_edgar     → finscope.providers.sec_edgar_provider
    #   finscope.mutual_funds  → finscope.providers.mfapi_provider
    #   finscope.ui (module)   → finscope.ui (package)


# ── Top-level API smoke tests ─────────────────────────────────────────────────

class TestTopLevelApiSmoke:
    def test_version_is_string(self):
        import finscope
        assert isinstance(finscope.__version__, str)

    def test_stock_factory_returns_stock(self):
        import finscope
        s = finscope.stock("AAPL")
        assert isinstance(s, finscope.Stock)
        assert s.symbol == "AAPL"

    def test_fund_factory_returns_fund(self):
        import finscope
        f = finscope.fund("VWRL.L")
        assert isinstance(f, finscope.Fund)
        assert f.symbol == "VWRL.L"

    def test_stock_is_lazy(self):
        """No network call should be made on construction."""
        import finscope
        mock_svc = MagicMock()
        s = finscope.Stock("AAPL", service=mock_svc)
        mock_svc.get_info.assert_not_called()

    def test_all_exports_resolvable(self):
        import finscope
        for name in finscope.__all__:
            assert hasattr(finscope, name), f"__all__ declares '{name}' but it's missing"


# ── Config smoke tests ────────────────────────────────────────────────────────

class TestConfigSmoke:
    def test_config_is_accessible(self):
        from finscope.config import config
        assert config is not None

    def test_config_has_defaults(self):
        from finscope.config import config
        assert config.request_timeout > 0
        assert config.sparkline_width > 0
        assert config.default_price_period == "1mo"

    def test_sec_user_agent_is_string(self):
        from finscope.config import config
        assert isinstance(config.sec_user_agent, str)
        assert "Finscope" in config.sec_user_agent

    def test_sec_headers_dict(self):
        from finscope.config import config
        headers = config.sec_headers
        assert "User-Agent" in headers
        assert "Accept-Encoding" in headers


# ── Exception smoke tests ─────────────────────────────────────────────────────

class TestExceptionsSmoke:
    def test_finscope_error_is_base(self):
        from finscope.exceptions import FinScopeError
        e = FinScopeError("test")
        assert isinstance(e, Exception)

    def test_backward_compat_alias(self):
        from finscope.exceptions import DashboardError, FinScopeError
        assert DashboardError is FinScopeError

    def test_ticker_not_found_message(self):
        from finscope.exceptions import TickerNotFoundError
        e = TickerNotFoundError("BADTICKER")
        assert "BADTICKER" in str(e)

    def test_data_fetch_error_message(self):
        from finscope.exceptions import DataFetchError
        e = DataFetchError("Yahoo Finance", "timeout")
        assert "Yahoo Finance" in str(e)
        assert "timeout" in str(e)

    def test_cik_not_found_message(self):
        from finscope.exceptions import CIKNotFoundError
        e = CIKNotFoundError("PRIVATE")
        assert "PRIVATE" in str(e)

    def test_fund_not_found_message(self):
        from finscope.exceptions import FundNotFoundError
        e = FundNotFoundError("BADCODE")
        assert "BADCODE" in str(e)

    def test_all_exceptions_inherit_finscope_error(self):
        from finscope.exceptions import (
            CIKNotFoundError,
            DataFetchError,
            FinScopeError,
            FundNotFoundError,
            InvalidPeriodError,
            TickerNotFoundError,
        )
        for cls in [
            TickerNotFoundError,
            DataFetchError,
            CIKNotFoundError,
            FundNotFoundError,
            InvalidPeriodError,
        ]:
            assert issubclass(cls, FinScopeError)


# ── Model construction smoke tests ────────────────────────────────────────────

class TestModelsSmoke:
    def test_key_ratios_from_empty_info(self):
        from finscope.models import KeyRatios
        ratios = KeyRatios.from_info({})
        assert ratios.pe_ratio is None

    def test_comparison_data_from_info(self):
        from finscope.models import ComparisonData
        info = {"quoteType": "EQUITY", "shortName": "Test", "currentPrice": 10.0}
        cd = ComparisonData.from_info("TEST", info)
        assert cd.symbol == "TEST"


# ── Provider construction smoke tests ─────────────────────────────────────────

class TestProviderConstruction:
    def test_yahoo_provider_instantiates(self):
        from finscope.providers.yahoo_provider import YahooFinanceProvider
        p = YahooFinanceProvider()
        assert p is not None

    def test_sec_edgar_provider_instantiates(self):
        from finscope.providers.sec_edgar_provider import SecEdgarProvider
        p = SecEdgarProvider()
        assert p is not None

    def test_mfapi_provider_instantiates(self):
        from finscope.providers.mfapi_provider import MfapiProvider
        p = MfapiProvider()
        assert p is not None


# ── Service construction smoke tests ──────────────────────────────────────────

class TestServiceConstruction:
    def test_stock_service_instantiates_with_defaults(self):
        from finscope.services.stock_service import StockAnalysisService
        s = StockAnalysisService()
        assert s is not None

    def test_fund_service_instantiates_with_defaults(self):
        from finscope.services.fund_service import FundAnalysisService
        s = FundAnalysisService()
        assert s is not None

    def test_stock_service_accepts_mock_providers(self):
        from finscope.services.stock_service import StockAnalysisService
        mock_yahoo = MagicMock()
        mock_sec = MagicMock()
        s = StockAnalysisService(yahoo=mock_yahoo, sec=mock_sec)
        assert s._yahoo is mock_yahoo
        assert s._sec is mock_sec


# ── CLI smoke tests ───────────────────────────────────────────────────────────

class TestCliSmoke:
    def test_main_entry_point_exists(self):
        from finscope.cli import main
        assert callable(main)

    def test_run_interactive_exists(self):
        from finscope.cli import run_interactive
        assert callable(run_interactive)

    def test_run_dashboard_alias(self):
        from finscope.cli import run_dashboard, run_interactive
        assert run_dashboard is run_interactive

    def test_run_interactive_returns_false_on_invalid_ticker(self):
        from finscope.cli import run_interactive
        from finscope.exceptions import TickerNotFoundError
        mock_service = MagicMock()
        mock_service.get_info.side_effect = TickerNotFoundError("INVALID")

        with patch("finscope.cli.console"):
            result = run_interactive(
                "INVALID",
                stock_service=mock_service,
                fund_service=MagicMock(),
            )
        assert result is False

    @patch("finscope.cli.Prompt.ask", return_value="exit")
    def test_dispatch_no_args_does_not_crash(self, mock_ask):
        from finscope.cli import _build_parser, _dispatch
        ns = _build_parser().parse_args([])
        with patch("finscope.cli._print_banner"), patch("finscope.cli.console"):
            _dispatch(ns)
        mock_ask.assert_called_once()

    def test_dispatch_ticker_routes_to_overview(self):
        from finscope.cli import _build_parser, _dispatch
        ns = _build_parser().parse_args(["AAPL"])
        with patch("finscope.cli.cmd_overview") as mock_cmd:
            _dispatch(ns)
        mock_cmd.assert_called_once_with("AAPL")

    def test_command_registry_has_17_numbered_options(self):
        from finscope.cli import _build_registry
        reg = _build_registry()
        for key in range(18):
            assert reg.label(key) != "", f"Key {key} not registered"

    def test_all_commands_are_concrete(self):
        from finscope.cli import DashboardCommand, _build_registry
        reg = _build_registry()
        for key, label in reg.items():
            cmd = reg.get(key)
            if key == 0:
                assert cmd is None
            else:
                assert isinstance(cmd, DashboardCommand), f"Key {key} not a command"


# ── Builder smoke test ────────────────────────────────────────────────────────

class TestBuilderSmoke:
    def test_table_builder_produces_rich_table(self):
        from finscope.ui.builders import TableBuilder
        from rich.table import Table

        table = (
            TableBuilder("Smoke Test")
            .column("A")
            .column("B")
            .row("hello", "world")
            .build()
        )
        assert isinstance(table, Table)
        assert table.row_count == 1


# ── Formatters smoke tests ────────────────────────────────────────────────────

class TestFormattersSmoke:
    def test_format_number_does_not_crash_on_none(self):
        from finscope.ui.formatters import format_number
        assert format_number(None) is not None

    def test_make_sparkline_does_not_crash_on_empty(self):
        from finscope.ui.formatters import make_sparkline
        result = make_sparkline([])
        assert isinstance(result, str)
