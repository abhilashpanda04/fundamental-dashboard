"""Unit tests for ``YahooFinanceProvider``.

All network calls are mocked; no real HTTP requests are made.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from finscope.exceptions import DataFetchError, TickerNotFoundError
from finscope.providers.yahoo_provider import YahooFinanceProvider


@pytest.fixture
def provider():
    return YahooFinanceProvider()


class TestGetInfo:
    def test_returns_info_dict(self, provider, apple_info, mock_yf_ticker):
        with patch("finscope.providers.yahoo_provider.yf.Ticker", return_value=mock_yf_ticker):
            result = provider.get_info("AAPL")
        assert result["symbol"] == "AAPL"
        assert result["quoteType"] == "EQUITY"

    def test_raises_ticker_not_found_when_empty(self, provider):
        mock = MagicMock()
        mock.info = {}
        with patch("finscope.providers.yahoo_provider.yf.Ticker", return_value=mock):
            with pytest.raises(TickerNotFoundError) as exc_info:
                provider.get_info("INVALID")
        assert "INVALID" in str(exc_info.value)

    def test_raises_ticker_not_found_when_no_quote_type(self, provider):
        mock = MagicMock()
        mock.info = {"longName": "Some Company"}  # missing quoteType
        with patch("finscope.providers.yahoo_provider.yf.Ticker", return_value=mock):
            with pytest.raises(TickerNotFoundError):
                provider.get_info("XYZ")

    def test_raises_data_fetch_error_on_exception(self, provider):
        mock = MagicMock()
        mock.info = property(lambda self: (_ for _ in ()).throw(RuntimeError("network error")))
        with patch("finscope.providers.yahoo_provider.yf.Ticker", side_effect=RuntimeError("net")):
            with pytest.raises(DataFetchError) as exc_info:
                provider.get_info("AAPL")
        assert "Yahoo Finance" in str(exc_info.value)


class TestGetPriceHistory:
    def test_returns_dataframe(self, provider, mock_yf_ticker, sample_price_df):
        with patch("finscope.providers.yahoo_provider.yf.Ticker", return_value=mock_yf_ticker):
            df = provider.get_price_history("AAPL", "1mo")
        assert isinstance(df, pd.DataFrame)
        assert not df.empty
        assert "Close" in df.columns

    def test_default_period_is_1mo(self, provider, mock_yf_ticker):
        with patch("finscope.providers.yahoo_provider.yf.Ticker", return_value=mock_yf_ticker):
            provider.get_price_history("AAPL")
        mock_yf_ticker.history.assert_called_once_with(period="1mo")

    def test_raises_data_fetch_error_on_exception(self, provider):
        with patch(
            "finscope.providers.yahoo_provider.yf.Ticker",
            side_effect=RuntimeError("timeout"),
        ):
            with pytest.raises(DataFetchError):
                provider.get_price_history("AAPL")


class TestGetSparkline:
    def test_returns_list_of_floats(self, provider, mock_yf_ticker):
        with patch("finscope.providers.yahoo_provider.yf.Ticker", return_value=mock_yf_ticker):
            result = provider.get_sparkline("AAPL")
        assert isinstance(result, list)
        assert all(isinstance(v, float) for v in result)

    def test_empty_df_returns_empty_list(self, provider):
        mock = MagicMock()
        mock.history.return_value = pd.DataFrame()
        with patch("finscope.providers.yahoo_provider.yf.Ticker", return_value=mock):
            result = provider.get_sparkline("AAPL")
        assert result == []

    def test_exception_returns_empty_list(self, provider):
        with patch(
            "finscope.providers.yahoo_provider.yf.Ticker",
            side_effect=RuntimeError("fail"),
        ):
            result = provider.get_sparkline("AAPL")
        assert result == []


class TestGetNews:
    def test_returns_list(self, provider, mock_yf_ticker, sample_news):
        with patch("finscope.providers.yahoo_provider.yf.Ticker", return_value=mock_yf_ticker):
            result = provider.get_news("AAPL")
        assert isinstance(result, list)
        assert len(result) == 2

    def test_returns_empty_list_on_exception(self, provider):
        with patch(
            "finscope.providers.yahoo_provider.yf.Ticker",
            side_effect=RuntimeError("fail"),
        ):
            result = provider.get_news("AAPL")
        assert result == []

    def test_returns_empty_list_when_news_none(self, provider):
        mock = MagicMock()
        mock.news = None
        with patch("finscope.providers.yahoo_provider.yf.Ticker", return_value=mock):
            result = provider.get_news("AAPL")
        assert result == []


class TestGetAnalystRecommendations:
    def test_returns_dataframe(self, provider, mock_yf_ticker):
        with patch("finscope.providers.yahoo_provider.yf.Ticker", return_value=mock_yf_ticker):
            result = provider.get_analyst_recommendations("AAPL")
        assert result is not None
        assert "strongBuy" in result.columns

    def test_returns_none_when_empty(self, provider):
        mock = MagicMock()
        mock.recommendations = pd.DataFrame()
        with patch("finscope.providers.yahoo_provider.yf.Ticker", return_value=mock):
            result = provider.get_analyst_recommendations("AAPL")
        assert result is None

    def test_returns_none_on_exception(self, provider):
        mock = MagicMock()
        type(mock).recommendations = property(
            lambda self: (_ for _ in ()).throw(RuntimeError("err"))
        )
        with patch("finscope.providers.yahoo_provider.yf.Ticker", return_value=mock):
            result = provider.get_analyst_recommendations("AAPL")
        assert result is None


class TestGetComparisonData:
    def test_returns_list_of_dicts(self, provider, mock_yf_ticker, apple_info):
        with patch("finscope.providers.yahoo_provider.yf.Ticker", return_value=mock_yf_ticker):
            result = provider.get_comparison_data(["AAPL"])
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["symbol"] == "AAPL"

    def test_skips_invalid_tickers(self, provider):
        mock = MagicMock()
        mock.info = {}  # No quoteType → TickerNotFoundError
        with patch("finscope.providers.yahoo_provider.yf.Ticker", return_value=mock):
            result = provider.get_comparison_data(["INVALID"])
        assert result == []

    def test_multiple_tickers(self, provider, mock_yf_ticker):
        with patch("finscope.providers.yahoo_provider.yf.Ticker", return_value=mock_yf_ticker):
            result = provider.get_comparison_data(["AAPL", "MSFT"])
        # Both use the same mock, so both succeed
        assert len(result) == 2


class TestSafeFloat:
    def test_none_returns_none(self, provider):
        assert provider._safe_float(None) is None

    def test_list_takes_first(self, provider):
        assert provider._safe_float([42.0]) == pytest.approx(42.0)

    def test_empty_list_returns_none(self, provider):
        assert provider._safe_float([]) is None

    def test_numeric_converts(self, provider):
        assert provider._safe_float(3.14) == pytest.approx(3.14)
