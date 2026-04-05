"""Unit and smoke tests for the ``finscope.Stock`` and ``finscope.Fund`` public API."""

from __future__ import annotations

from unittest.mock import MagicMock, patch, PropertyMock

import pandas as pd
import pytest

from finscope.stock import Stock, Fund


# ── Stock ─────────────────────────────────────────────────────────────────────


@pytest.fixture
def mock_stock_service(apple_info, sample_price_df, sample_news, sample_financials_df):
    m = MagicMock()
    m.get_info.return_value = apple_info
    m.get_key_ratios.return_value = MagicMock(
        pe_ratio=28.5,
        market_cap=2_700_000_000_000,
        to_display_dict=lambda: {"P/E Ratio": 28.5},
    )
    m.get_sparkline.return_value = [100.0, 105.0, 110.0]
    m.get_price_history.return_value = sample_price_df
    m.get_news.return_value = sample_news
    m.get_financials.return_value = sample_financials_df
    m.get_balance_sheet.return_value = sample_financials_df
    m.get_cashflow.return_value = sample_financials_df
    m.get_analyst_recommendations.return_value = None
    m.get_major_holders.return_value = (None, None)
    m.get_detailed_financials.return_value = {}
    m.get_recent_filings.return_value = []
    m.get_insider_transactions.return_value = []
    m.get_comparison_data.return_value = []
    m.build_export_data.return_value = {
        "info": apple_info,
        "ratios": {"P/E Ratio": 28.5},
        "price_history": sample_price_df,
    }
    return m


class TestStockConstruction:
    def test_symbol_uppercased(self, mock_stock_service):
        s = Stock("aapl", service=mock_stock_service)
        assert s.symbol == "AAPL"

    def test_no_network_on_construction(self, mock_stock_service):
        s = Stock("AAPL", service=mock_stock_service)
        # Nothing should be called until we access a property
        mock_stock_service.get_info.assert_not_called()
        mock_stock_service.get_sparkline.assert_not_called()


class TestStockInfo:
    def test_info_returns_dict(self, mock_stock_service, apple_info):
        s = Stock("AAPL", service=mock_stock_service)
        assert s.info["symbol"] == "AAPL"
        mock_stock_service.get_info.assert_called_once_with("AAPL")

    def test_info_cached(self, mock_stock_service):
        s = Stock("AAPL", service=mock_stock_service)
        _ = s.info
        _ = s.info  # second access
        mock_stock_service.get_info.assert_called_once()  # only one call


class TestStockRatios:
    def test_ratios_returns_key_ratios(self, mock_stock_service):
        s = Stock("AAPL", service=mock_stock_service)
        assert s.ratios.pe_ratio == pytest.approx(28.5)

    def test_ratios_cached(self, mock_stock_service):
        s = Stock("AAPL", service=mock_stock_service)
        _ = s.ratios
        _ = s.ratios
        mock_stock_service.get_key_ratios.assert_called_once()


class TestStockPriceData:
    def test_sparkline_returns_list(self, mock_stock_service):
        s = Stock("AAPL", service=mock_stock_service)
        assert s.sparkline == [100.0, 105.0, 110.0]
        mock_stock_service.get_sparkline.assert_called_once_with("AAPL", period="3mo")

    def test_price_history_returns_df(self, mock_stock_service, sample_price_df):
        s = Stock("AAPL", service=mock_stock_service)
        df = s.price_history("1y")
        mock_stock_service.get_price_history.assert_called_once_with("AAPL", "1y")
        assert isinstance(df, pd.DataFrame)

    def test_price_history_default_period(self, mock_stock_service):
        s = Stock("AAPL", service=mock_stock_service)
        s.price_history()
        mock_stock_service.get_price_history.assert_called_once_with("AAPL", "1mo")


class TestStockFinancials:
    def test_financials_cached(self, mock_stock_service):
        s = Stock("AAPL", service=mock_stock_service)
        _ = s.financials
        _ = s.financials
        mock_stock_service.get_financials.assert_called_once()

    def test_balance_sheet(self, mock_stock_service):
        s = Stock("AAPL", service=mock_stock_service)
        assert isinstance(s.balance_sheet, pd.DataFrame)

    def test_cashflow(self, mock_stock_service):
        s = Stock("AAPL", service=mock_stock_service)
        assert isinstance(s.cashflow, pd.DataFrame)


class TestStockQualitative:
    def test_news_returns_list(self, mock_stock_service, sample_news):
        s = Stock("AAPL", service=mock_stock_service)
        assert s.news == sample_news

    def test_analyst_recommendations(self, mock_stock_service):
        s = Stock("AAPL", service=mock_stock_service)
        assert s.analyst_recommendations is None

    def test_holders_returns_tuple(self, mock_stock_service):
        s = Stock("AAPL", service=mock_stock_service)
        breakdown, institutional = s.holders
        assert breakdown is None
        assert institutional is None


class TestStockSec:
    def test_sec_financials(self, mock_stock_service):
        s = Stock("AAPL", service=mock_stock_service)
        assert s.sec_financials == {}

    def test_sec_filings(self, mock_stock_service):
        s = Stock("AAPL", service=mock_stock_service)
        assert s.sec_filings(count=5) == []
        mock_stock_service.get_recent_filings.assert_called_once_with("AAPL", count=5)

    def test_insider_transactions(self, mock_stock_service):
        s = Stock("AAPL", service=mock_stock_service)
        assert s.insider_transactions == []


class TestStockComparison:
    def test_compare_with(self, mock_stock_service):
        s = Stock("AAPL", service=mock_stock_service)
        s.compare_with("MSFT", "GOOGL")
        mock_stock_service.get_comparison_data.assert_called_once_with(
            ["AAPL", "MSFT", "GOOGL"]
        )


class TestStockExport:
    def test_export_html_default_path(self, mock_stock_service):
        s = Stock("AAPL", service=mock_stock_service)
        with patch("finscope.ui.export_to_html") as mock_export:
            path = s.export_html()
        assert path == "aapl_report.html"
        mock_export.assert_called_once()

    def test_export_html_custom_path(self, mock_stock_service):
        s = Stock("AAPL", service=mock_stock_service)
        with patch("finscope.ui.export_to_html"):
            path = s.export_html("custom.html")
        assert path == "custom.html"


class TestStockDunder:
    def test_repr_with_info(self, mock_stock_service):
        s = Stock("AAPL", service=mock_stock_service)
        r = repr(s)
        assert "AAPL" in r
        assert "Apple" in r
        assert "175.5" in r

    def test_repr_without_info(self):
        """repr should not crash when info fetch would fail."""
        mock_svc = MagicMock()
        mock_svc.get_info.side_effect = Exception("offline")
        s = Stock("AAPL", service=mock_svc)
        r = repr(s)
        assert "AAPL" in r

    def test_str_same_as_repr(self, mock_stock_service):
        s = Stock("AAPL", service=mock_stock_service)
        assert str(s) == repr(s)

    def test_equality(self, mock_stock_service):
        a = Stock("AAPL", service=mock_stock_service)
        b = Stock("AAPL", service=mock_stock_service)
        c = Stock("MSFT", service=mock_stock_service)
        assert a == b
        assert a != c

    def test_hash(self, mock_stock_service):
        a = Stock("AAPL", service=mock_stock_service)
        b = Stock("AAPL", service=mock_stock_service)
        assert hash(a) == hash(b)
        assert {a, b} == {a}  # same hash → deduplicated in set

    def test_not_equal_to_other_types(self, mock_stock_service):
        s = Stock("AAPL", service=mock_stock_service)
        assert s != "AAPL"
        assert s != 42


# ── Fund ──────────────────────────────────────────────────────────────────────


@pytest.fixture
def mock_fund_service():
    m = MagicMock()
    m.get_global_fund_info.return_value = {
        "shortName": "Vanguard FTSE All-World",
        "quoteType": "ETF",
        "currency": "GBP",
    }
    m.get_global_fund_returns.return_value = {"1Y": 12.5, "3Y": 8.2}
    m.get_global_fund_sparkline.return_value = [100.0, 105.0, 110.0]
    return m


class TestFundConstruction:
    def test_symbol_uppercased(self, mock_fund_service):
        f = Fund("vwrl.l", service=mock_fund_service)
        assert f.symbol == "VWRL.L"

    def test_no_network_on_construction(self, mock_fund_service):
        f = Fund("VWRL.L", service=mock_fund_service)
        mock_fund_service.get_global_fund_info.assert_not_called()


class TestFundProperties:
    def test_info(self, mock_fund_service):
        f = Fund("VWRL.L", service=mock_fund_service)
        assert f.info["shortName"] == "Vanguard FTSE All-World"

    def test_returns(self, mock_fund_service):
        f = Fund("VWRL.L", service=mock_fund_service)
        assert f.returns["1Y"] == 12.5

    def test_sparkline(self, mock_fund_service):
        f = Fund("VWRL.L", service=mock_fund_service)
        assert f.sparkline == [100.0, 105.0, 110.0]

    def test_info_cached(self, mock_fund_service):
        f = Fund("VWRL.L", service=mock_fund_service)
        _ = f.info
        _ = f.info
        mock_fund_service.get_global_fund_info.assert_called_once()


class TestFundDunder:
    def test_repr(self, mock_fund_service):
        f = Fund("VWRL.L", service=mock_fund_service)
        r = repr(f)
        assert "VWRL.L" in r
        assert "Vanguard" in r

    def test_equality(self, mock_fund_service):
        a = Fund("VWRL.L", service=mock_fund_service)
        b = Fund("VWRL.L", service=mock_fund_service)
        c = Fund("INDA", service=mock_fund_service)
        assert a == b
        assert a != c

    def test_hash(self, mock_fund_service):
        a = Fund("VWRL.L", service=mock_fund_service)
        b = Fund("VWRL.L", service=mock_fund_service)
        assert hash(a) == hash(b)


# ── Top-level API tests ──────────────────────────────────────────────────────


class TestTopLevelApi:
    def test_stock_factory(self):
        import finscope
        s = finscope.stock("AAPL")
        assert isinstance(s, Stock)
        assert s.symbol == "AAPL"

    def test_fund_factory(self):
        import finscope
        f = finscope.fund("VWRL.L")
        assert isinstance(f, Fund)
        assert f.symbol == "VWRL.L"

    def test_compare_factory(self):
        import finscope
        with patch.object(
            finscope.StockAnalysisService,
            "get_comparison_data",
            return_value=[],
        ):
            result = finscope.compare("AAPL", "MSFT")
        assert isinstance(result, list)

    def test_version_exists(self):
        import finscope
        assert hasattr(finscope, "__version__")
        assert isinstance(finscope.__version__, str)

    def test_all_exports_exist(self):
        import finscope
        for name in finscope.__all__:
            assert hasattr(finscope, name), f"Missing export: {name}"
