"""Unit tests for ``StockAnalysisService`` (Facade Pattern)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from dashboard.exceptions import DataFetchError, TickerNotFoundError
from dashboard.models import ComparisonData, KeyRatios
from dashboard.providers.sec_edgar_provider import SecEdgarProvider
from dashboard.providers.yahoo_provider import YahooFinanceProvider
from dashboard.services.stock_service import StockAnalysisService


@pytest.fixture
def mock_yahoo(apple_info, sample_price_df, sample_news):
    """Mock YahooFinanceProvider with sensible return values."""
    m = MagicMock(spec=YahooFinanceProvider)
    m.get_info.return_value = apple_info
    m.get_price_history.return_value = sample_price_df
    m.get_sparkline.return_value = [100.0, 105.0, 110.0]
    m.get_news.return_value = sample_news
    m.get_analyst_recommendations.return_value = None
    m.get_major_holders.return_value = (None, None)
    m.get_financials.return_value = sample_price_df
    m.get_balance_sheet.return_value = sample_price_df
    m.get_cashflow.return_value = sample_price_df
    m.get_comparison_data.return_value = []
    return m


@pytest.fixture
def mock_sec():
    m = MagicMock(spec=SecEdgarProvider)
    m.get_detailed_financials.return_value = {}
    m.get_recent_filings.return_value = []
    m.get_insider_transactions.return_value = []
    return m


@pytest.fixture
def service(mock_yahoo, mock_sec):
    return StockAnalysisService(yahoo=mock_yahoo, sec=mock_sec)


class TestGetInfo:
    def test_delegates_to_yahoo(self, service, mock_yahoo, apple_info):
        result = service.get_info("AAPL")
        mock_yahoo.get_info.assert_called_once_with("AAPL")
        assert result["symbol"] == "AAPL"

    def test_propagates_ticker_not_found(self, service, mock_yahoo):
        mock_yahoo.get_info.side_effect = TickerNotFoundError("INVALID")
        with pytest.raises(TickerNotFoundError):
            service.get_info("INVALID")


class TestGetKeyRatios:
    def test_returns_key_ratios_instance(self, service, apple_info):
        ratios = service.get_key_ratios(apple_info)
        assert isinstance(ratios, KeyRatios)
        assert ratios.pe_ratio == pytest.approx(28.5)

    def test_to_display_dict_has_all_labels(self, service, apple_info):
        ratios = service.get_key_ratios(apple_info)
        display = ratios.to_display_dict()
        assert "P/E Ratio" in display
        assert "Market Cap" in display


class TestGetPriceHistory:
    def test_returns_dataframe(self, service, mock_yahoo, sample_price_df):
        df = service.get_price_history("AAPL")
        mock_yahoo.get_price_history.assert_called_once_with("AAPL", "1mo")
        assert isinstance(df, pd.DataFrame)

    def test_custom_period_forwarded(self, service, mock_yahoo):
        service.get_price_history("AAPL", period="3mo")
        mock_yahoo.get_price_history.assert_called_once_with("AAPL", "3mo")


class TestGetSparkline:
    def test_returns_list(self, service, mock_yahoo):
        result = service.get_sparkline("AAPL")
        assert isinstance(result, list)
        assert len(result) == 3


class TestGetComparisonData:
    def test_converts_dicts_to_comparison_data(self, service, mock_yahoo, sample_comparison_data):
        mock_yahoo.get_comparison_data.return_value = sample_comparison_data
        result = service.get_comparison_data(["AAPL", "MSFT"])
        assert isinstance(result, list)
        assert all(isinstance(cd, ComparisonData) for cd in result)
        assert result[0].symbol == "AAPL"
        assert result[1].symbol == "MSFT"

    def test_sparkline_preserved(self, service, mock_yahoo, sample_comparison_data):
        mock_yahoo.get_comparison_data.return_value = sample_comparison_data
        result = service.get_comparison_data(["AAPL"])
        assert result[0].sparkline == [100.0, 105.0, 110.0]

    def test_empty_input_returns_empty(self, service, mock_yahoo):
        mock_yahoo.get_comparison_data.return_value = []
        result = service.get_comparison_data([])
        assert result == []


class TestSecMethods:
    def test_get_detailed_financials_delegates(self, service, mock_sec):
        result = service.get_detailed_financials("AAPL")
        mock_sec.get_detailed_financials.assert_called_once_with("AAPL")
        assert result == {}

    def test_get_recent_filings_delegates(self, service, mock_sec):
        result = service.get_recent_filings("AAPL", count=10)
        mock_sec.get_recent_filings.assert_called_once_with("AAPL", count=10)
        assert result == []

    def test_get_recent_filings_returns_empty_on_error(self, service, mock_sec):
        mock_sec.get_recent_filings.side_effect = DataFetchError("SEC EDGAR", "timeout")
        result = service.get_recent_filings("AAPL")
        assert result == []

    def test_get_insider_transactions_delegates(self, service, mock_sec):
        result = service.get_insider_transactions("AAPL")
        mock_sec.get_insider_transactions.assert_called_once_with("AAPL")


class TestBuildExportData:
    def test_returns_required_keys(self, service, mock_yahoo, apple_info):
        data = service.build_export_data("AAPL")
        assert "info" in data
        assert "ratios" in data
        assert "price_history" in data

    def test_ratios_is_display_dict(self, service, apple_info):
        data = service.build_export_data("AAPL")
        assert "P/E Ratio" in data["ratios"]
