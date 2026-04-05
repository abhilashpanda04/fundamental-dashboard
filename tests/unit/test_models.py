"""Unit tests for domain models in ``dashboard.models``."""

from __future__ import annotations

import pytest

from dashboard.models import (
    ComparisonData,
    FundReturn,
    IndiaFundMeta,
    KeyRatios,
    NavRecord,
    PriceBar,
    SecFiling,
    StockQuote,
)
from datetime import datetime


class TestKeyRatios:
    def test_from_info_populates_fields(self, apple_info):
        ratios = KeyRatios.from_info(apple_info)
        assert ratios.pe_ratio == pytest.approx(28.5)
        assert ratios.forward_pe == pytest.approx(25.0)
        assert ratios.market_cap == 2_700_000_000_000
        assert ratios.beta == pytest.approx(1.29)

    def test_from_info_missing_keys_are_none(self):
        ratios = KeyRatios.from_info({})
        assert ratios.pe_ratio is None
        assert ratios.market_cap is None
        assert ratios.dividend_yield is None

    def test_to_display_dict_contains_all_labels(self, apple_info):
        ratios = KeyRatios.from_info(apple_info)
        display = ratios.to_display_dict()
        assert "P/E Ratio" in display
        assert "Market Cap" in display
        assert "Beta" in display
        assert "52W High" in display
        assert len(display) == 23

    def test_to_display_dict_values_match_fields(self, apple_info):
        ratios = KeyRatios.from_info(apple_info)
        display = ratios.to_display_dict()
        assert display["P/E Ratio"] == ratios.pe_ratio
        assert display["Market Cap"] == ratios.market_cap

    def test_from_info_with_partial_data(self):
        partial = {"trailingPE": 20.0, "beta": 1.1}
        ratios = KeyRatios.from_info(partial)
        assert ratios.pe_ratio == pytest.approx(20.0)
        assert ratios.beta == pytest.approx(1.1)
        assert ratios.roe is None


class TestComparisonData:
    def test_from_info_factory(self, apple_info):
        cd = ComparisonData.from_info("AAPL", apple_info, sparkline=[100.0, 110.0])
        assert cd.symbol == "AAPL"
        assert cd.name == "Apple Inc."
        assert cd.price == pytest.approx(175.50)
        assert cd.sparkline == [100.0, 110.0]

    def test_from_info_symbol_uppercased(self, apple_info):
        cd = ComparisonData.from_info("aapl", apple_info)
        assert cd.symbol == "AAPL"

    def test_from_info_empty_sparkline_default(self, apple_info):
        cd = ComparisonData.from_info("AAPL", apple_info)
        assert cd.sparkline == []

    def test_from_info_missing_price_falls_back(self):
        info = {"quoteType": "EQUITY", "regularMarketPrice": 99.0, "shortName": "Test Co"}
        cd = ComparisonData.from_info("TEST", info)
        assert cd.price == pytest.approx(99.0)


class TestStockQuote:
    def test_default_currency(self):
        q = StockQuote(symbol="AAPL", name="Apple", price=175.0, change_pct=1.0)
        assert q.currency == "USD"
        assert q.sector == "N/A"

    def test_custom_values(self):
        q = StockQuote(
            symbol="RELIANCE.NS",
            name="Reliance Industries",
            price=2500.0,
            change_pct=-0.5,
            currency="INR",
            exchange="NSE",
        )
        assert q.currency == "INR"
        assert q.exchange == "NSE"


class TestPriceBar:
    def test_creation(self):
        bar = PriceBar(
            date=datetime(2024, 1, 1),
            open=150.0,
            high=155.0,
            low=148.0,
            close=153.0,
            volume=1_000_000,
        )
        assert bar.close == pytest.approx(153.0)
        assert bar.volume == 1_000_000


class TestSecFiling:
    def test_creation(self, sample_sec_filing):
        f = SecFiling(**sample_sec_filing)
        assert f.form == "10-K"
        assert f.date == "2023-11-03"
        assert "aapl" in f.url


class TestIndiaFundMeta:
    def test_creation(self):
        meta = IndiaFundMeta(
            scheme_code="125497",
            scheme_name="SBI Small Cap Fund - Direct Plan - Growth",
            fund_house="SBI Mutual Fund",
            scheme_category="Small Cap Fund",
            scheme_type="Open Ended Schemes",
            isin="INF200K01LU8",
        )
        assert meta.scheme_code == "125497"
        assert meta.isin == "INF200K01LU8"

    def test_isin_optional(self):
        meta = IndiaFundMeta(
            scheme_code="999",
            scheme_name="Test Fund",
            fund_house="Test AMC",
            scheme_category="Equity",
            scheme_type="Open Ended",
        )
        assert meta.isin is None


class TestFundReturn:
    def test_creation(self):
        fr = FundReturn(
            period="1Y",
            return_pct=15.5,
            start_nav=90.0,
            current_nav=104.5,
            start_date="04-01-2023",
        )
        assert fr.return_pct == pytest.approx(15.5)
