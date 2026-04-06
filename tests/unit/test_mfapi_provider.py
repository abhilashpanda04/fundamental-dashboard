"""Unit tests for ``MfapiProvider``."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from finscope.exceptions import FundNotFoundError
from finscope.providers.mfapi_provider import MfapiProvider, POPULAR_FUNDS


@pytest.fixture
def provider():
    return MfapiProvider()


@pytest.fixture
def nav_data():
    """NAV data spanning ~2 years (newest first), anchored to today."""
    from datetime import datetime, timedelta
    base = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    records = []
    for i in range(730):
        d = base - timedelta(days=i)
        # Skip weekends
        if d.weekday() < 5:
            nav = 100.0 + i * 0.02  # Gently increasing from past → present
            records.append({
                "date": d.strftime("%d-%m-%Y"),
                "nav": f"{nav:.4f}",
            })
    return records


class TestSearchFunds:
    def test_returns_list_from_api(self, provider):
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {"schemeCode": 125497, "schemeName": "SBI Small Cap Fund - Direct - Growth"},
            {"schemeCode": 120503, "schemeName": "SBI Bluechip Fund - Direct - Growth"},
        ]
        mock_response.raise_for_status = MagicMock()

        with patch("finscope.providers.mfapi_provider.requests.get", return_value=mock_response):
            results = provider.search_funds("SBI")

        assert len(results) == 2
        assert results[0]["schemeCode"] == 125497

    def test_falls_back_to_local_search_on_error(self, provider):
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = Exception("API error")

        all_funds = [
            {"schemeCode": 1, "schemeName": "SBI Small Cap Fund"},
            {"schemeCode": 2, "schemeName": "HDFC Midcap Fund"},
        ]

        with (
            patch("finscope.providers.mfapi_provider.requests.get", return_value=mock_response),
            patch.object(provider, "_all_india_funds", return_value=all_funds),
        ):
            results = provider.search_funds("SBI")

        assert len(results) == 1
        assert results[0]["schemeName"] == "SBI Small Cap Fund"

    def test_local_search_case_insensitive(self, provider):
        all_funds = [
            {"schemeCode": 1, "schemeName": "SBI Small Cap Fund"},
        ]
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = Exception("err")

        with (
            patch("finscope.providers.mfapi_provider.requests.get", return_value=mock_response),
            patch.object(provider, "_all_india_funds", return_value=all_funds),
        ):
            results = provider.search_funds("sbi small cap")

        assert len(results) == 1


class TestGetFundDetail:
    def test_returns_dict_on_success(self, provider):
        fund_detail = {
            "meta": {
                "scheme_name": "SBI Small Cap Fund",
                "fund_house": "SBI Mutual Fund",
            },
            "data": [{"date": "04-01-2024", "nav": "105.23"}],
        }
        mock_response = MagicMock()
        mock_response.json.return_value = fund_detail
        mock_response.raise_for_status = MagicMock()

        with patch("finscope.providers.mfapi_provider.requests.get", return_value=mock_response):
            result = provider.get_fund_detail("125497")

        assert result["meta"]["scheme_name"] == "SBI Small Cap Fund"
        assert len(result["data"]) == 1

    def test_raises_fund_not_found_on_http_error(self, provider):
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = Exception("404")

        with patch("finscope.providers.mfapi_provider.requests.get", return_value=mock_response):
            with pytest.raises(FundNotFoundError):
                provider.get_fund_detail("INVALID_CODE")


class TestCalculateReturns:
    def test_calculates_1w_return(self, nav_data):
        returns = MfapiProvider._calculate_returns(nav_data)
        assert "1W" in returns
        assert returns["1W"]["return_pct"] is not None

    def test_calculates_1y_return(self, nav_data):
        returns = MfapiProvider._calculate_returns(nav_data)
        assert "1Y" in returns
        assert isinstance(returns["1Y"]["return_pct"], float)

    def test_return_dict_has_expected_keys(self, nav_data):
        returns = MfapiProvider._calculate_returns(nav_data)
        period = returns.get("1M") or returns.get("1W")
        assert period is not None
        assert "return_pct" in period
        assert "start_nav" in period
        assert "current_nav" in period
        assert "start_date" in period

    def test_empty_nav_data_returns_empty(self):
        assert MfapiProvider._calculate_returns([]) == {}

    def test_insufficient_history_skips_period(self):
        # Only 1 day of data — no 1Y return possible
        nav_data = [{"date": "04-01-2024", "nav": "100.0"}]
        returns = MfapiProvider._calculate_returns(nav_data)
        assert "1Y" not in returns

    def test_positive_return_for_growing_nav(self):
        # Latest NAV is higher than 1 year ago
        nav_data = [
            {"date": "04-01-2024", "nav": "120.0"},  # Current
            {"date": "04-01-2023", "nav": "100.0"},  # 1 year ago
        ]
        returns = MfapiProvider._calculate_returns(nav_data)
        assert "1Y" in returns
        assert returns["1Y"]["return_pct"] == pytest.approx(20.0)

    def test_negative_return_for_declining_nav(self):
        nav_data = [
            {"date": "04-01-2024", "nav": "80.0"},
            {"date": "04-01-2023", "nav": "100.0"},
        ]
        returns = MfapiProvider._calculate_returns(nav_data)
        assert returns["1Y"]["return_pct"] == pytest.approx(-20.0)


class TestNavSeries:
    def test_returns_float_list(self, nav_data):
        result = MfapiProvider._nav_series(nav_data, days=365)
        assert isinstance(result, list)
        assert all(isinstance(v, float) for v in result)

    def test_oldest_to_newest_order(self, nav_data):
        result = MfapiProvider._nav_series(nav_data, days=365)
        # Full series for 1 year should be oldest first
        assert len(result) > 0

    def test_empty_nav_data(self):
        assert MfapiProvider._nav_series([], days=365) == []

    def test_shorter_period_gives_fewer_points(self, nav_data):
        full = MfapiProvider._nav_series(nav_data, days=365)
        short = MfapiProvider._nav_series(nav_data, days=30)
        assert len(short) <= len(full)


class TestGlobalPriceHistory:
    def test_get_price_history_returns_dataframe_from_yfinance(self, provider):
        expected = pd.DataFrame({"Close": [100.0, 101.5]})
        ticker = MagicMock()
        ticker.history.return_value = expected

        with patch("finscope.providers.mfapi_provider.yf.Ticker", return_value=ticker) as mock_ticker:
            result = provider.get_price_history("VFIAX", period="3mo")

        mock_ticker.assert_called_once_with("VFIAX")
        ticker.history.assert_called_once_with(period="3mo")
        assert result.equals(expected)

    def test_get_price_history_returns_empty_dataframe_and_logs_warning_on_error(self, provider, caplog):
        ticker = MagicMock()
        ticker.history.side_effect = Exception("boom")

        with patch("finscope.providers.mfapi_provider.yf.Ticker", return_value=ticker):
            result = provider.get_price_history("VFIAX", period="1mo")

        assert result.empty
        assert "Global fund price history for VFIAX" in caplog.text


class TestPopularFunds:
    def test_popular_funds_dict_has_expected_regions(self):
        expected_regions = {
            "US",
            "Global ETF (LSE)",
            "Asia Pacific ETF",
            "European ETF",
            "Fixed Income / Bond ETF",
        }
        assert expected_regions.issubset(set(POPULAR_FUNDS.keys()))

    def test_each_region_has_entries(self):
        for region, funds in POPULAR_FUNDS.items():
            assert len(funds) > 0, f"No funds for region: {region}"

    def test_each_entry_is_symbol_description_pair(self):
        for region, funds in POPULAR_FUNDS.items():
            for entry in funds:
                assert len(entry) == 2, f"Expected (symbol, description) in {region}"
                symbol, desc = entry
                assert isinstance(symbol, str) and len(symbol) > 0
                assert isinstance(desc, str) and len(desc) > 0
