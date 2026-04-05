"""Unit tests for ``FundAnalysisService`` (Facade Pattern)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from dashboard.providers.mfapi_provider import MfapiProvider
from dashboard.services.fund_service import FundAnalysisService


@pytest.fixture
def mock_provider():
    m = MagicMock(spec=MfapiProvider)
    m.search_funds.return_value = []
    m.get_fund_detail.return_value = None
    m.get_global_fund_info.return_value = None
    m.get_global_fund_returns.return_value = {}
    m.get_global_fund_sparkline.return_value = []
    m.get_popular_funds_snapshot.return_value = []
    return m


@pytest.fixture
def service(mock_provider):
    return FundAnalysisService(provider=mock_provider)


class TestSearchIndiaFunds:
    def test_delegates_to_provider(self, service, mock_provider):
        mock_provider.search_funds.return_value = [
            {"schemeCode": 125497, "schemeName": "SBI Small Cap"}
        ]
        result = service.search_india_funds("SBI")
        mock_provider.search_funds.assert_called_once_with("SBI")
        assert len(result) == 1

    def test_returns_empty_on_empty_result(self, service, mock_provider):
        mock_provider.search_funds.return_value = []
        result = service.search_india_funds("nonexistent")
        assert result == []


class TestGetIndiaFundDetail:
    def test_returns_detail_dict(self, service, mock_provider):
        mock_provider.get_fund_detail.return_value = {
            "meta": {"scheme_name": "SBI Small Cap"},
            "data": [{"date": "04-01-2024", "nav": "105.23"}],
        }
        result = service.get_india_fund_detail("125497")
        mock_provider.get_fund_detail.assert_called_once_with("125497")
        assert result["meta"]["scheme_name"] == "SBI Small Cap"

    def test_returns_none_on_fund_not_found(self, service, mock_provider):
        from dashboard.exceptions import FundNotFoundError
        mock_provider.get_fund_detail.side_effect = FundNotFoundError("INVALID")
        result = service.get_india_fund_detail("INVALID")
        assert result is None


class TestCalculateIndiaFundReturns:
    def test_delegates_to_provider(self, service, mock_provider, sample_nav_data):
        mock_provider._calculate_returns.return_value = {"1Y": {"return_pct": 15.0}}
        result = service.calculate_india_fund_returns(sample_nav_data)
        mock_provider._calculate_returns.assert_called_once_with(sample_nav_data)
        assert "1Y" in result


class TestGetIndiaFundNavSeries:
    def test_delegates_to_provider(self, service, mock_provider, sample_nav_data):
        mock_provider._nav_series.return_value = [100.0, 105.0]
        result = service.get_india_fund_nav_series(sample_nav_data, days=365)
        mock_provider._nav_series.assert_called_once_with(sample_nav_data, days=365)
        assert result == [100.0, 105.0]


class TestGlobalFundMethods:
    def test_get_global_fund_info_delegates(self, service, mock_provider):
        mock_provider.get_global_fund_info.return_value = {"longName": "Vanguard 500"}
        result = service.get_global_fund_info("VFIAX")
        mock_provider.get_global_fund_info.assert_called_once_with("VFIAX")
        assert result["longName"] == "Vanguard 500"

    def test_get_global_fund_returns_delegates(self, service, mock_provider):
        mock_provider.get_global_fund_returns.return_value = {"1Y": 12.5}
        result = service.get_global_fund_returns("VFIAX")
        assert result == {"1Y": 12.5}

    def test_get_global_fund_sparkline_delegates(self, service, mock_provider):
        mock_provider.get_global_fund_sparkline.return_value = [100.0, 110.0]
        result = service.get_global_fund_sparkline("VFIAX", period="1y")
        assert result == [100.0, 110.0]

    def test_get_popular_funds_snapshot_delegates(self, service, mock_provider):
        mock_provider.get_popular_funds_snapshot.return_value = [{"symbol": "VFIAX"}]
        result = service.get_popular_funds_snapshot("US")
        mock_provider.get_popular_funds_snapshot.assert_called_once_with("US")
        assert len(result) == 1


class TestPopularFundRegions:
    def test_returns_list_of_strings(self, service):
        regions = service.popular_fund_regions
        assert isinstance(regions, list)
        assert all(isinstance(r, str) for r in regions)

    def test_includes_expected_regions(self, service):
        regions = service.popular_fund_regions
        assert "US" in regions
        assert "Asia Pacific ETF" in regions
