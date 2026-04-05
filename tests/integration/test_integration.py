"""Integration tests — make real network calls to external APIs.

These tests are marked ``@pytest.mark.integration`` and are *excluded* from
the default test run.  Run them explicitly when you want to verify live API
connectivity:

    pytest -m integration -v

Requirements:
- A working internet connection
- Yahoo Finance must be reachable
- SEC EDGAR must be reachable
- MFAPI.in must be reachable (for the Indian fund tests)

These tests use well-known, stable symbols / scheme codes that are unlikely
to change (AAPL, SBI Small Cap Fund Direct Growth).
"""

from __future__ import annotations

import pytest


pytestmark = pytest.mark.integration


# ── Yahoo Finance ─────────────────────────────────────────────────────────────

class TestYahooIntegration:
    @pytest.fixture(scope="class")
    def provider(self):
        from dashboard.providers.yahoo_provider import YahooFinanceProvider
        return YahooFinanceProvider()

    def test_get_info_aapl(self, provider):
        info = provider.get_info("AAPL")
        assert info["symbol"] == "AAPL"
        assert "quoteType" in info
        assert isinstance(info.get("currentPrice") or info.get("regularMarketPrice"), float)

    def test_get_price_history_1mo(self, provider):
        import pandas as pd
        df = provider.get_price_history("AAPL", "1mo")
        assert isinstance(df, pd.DataFrame)
        assert not df.empty
        assert "Close" in df.columns

    def test_get_sparkline_returns_floats(self, provider):
        sparkline = provider.get_sparkline("AAPL", "3mo")
        assert isinstance(sparkline, list)
        assert len(sparkline) > 0
        assert all(isinstance(v, float) for v in sparkline)

    def test_get_news_returns_list(self, provider):
        news = provider.get_news("AAPL")
        assert isinstance(news, list)

    def test_ticker_not_found_raises_error(self, provider):
        from dashboard.exceptions import TickerNotFoundError
        with pytest.raises(TickerNotFoundError):
            provider.get_info("ZZZZNOTAREALTICKER99")

    def test_get_financials_aapl(self, provider):
        import pandas as pd
        df = provider.get_financials("AAPL")
        # May be empty due to yfinance changes but should not raise
        assert isinstance(df, pd.DataFrame)

    def test_comparison_data_two_tickers(self, provider):
        result = provider.get_comparison_data(["AAPL", "MSFT"])
        symbols = {d["symbol"] for d in result}
        assert "AAPL" in symbols or "MSFT" in symbols


# ── SEC EDGAR ─────────────────────────────────────────────────────────────────

class TestSecEdgarIntegration:
    @pytest.fixture(scope="class")
    def provider(self):
        from dashboard.providers.sec_edgar_provider import SecEdgarProvider
        return SecEdgarProvider()

    def test_get_cik_apple(self, provider):
        cik = provider.get_cik("AAPL")
        assert cik == "0000320193"

    def test_get_cik_microsoft(self, provider):
        cik = provider.get_cik("MSFT")
        # CIK for Microsoft
        assert cik.lstrip("0") == "789019"

    def test_get_cik_not_found_raises(self, provider):
        from dashboard.exceptions import CIKNotFoundError
        with pytest.raises(CIKNotFoundError):
            provider.get_cik("ZZZZNOTAREALTICKER99")

    def test_get_company_facts_returns_dict(self, provider):
        facts = provider.get_company_facts("AAPL")
        assert "entityName" in facts
        assert "facts" in facts
        assert "us-gaap" in facts["facts"]

    def test_extract_net_income_10k(self, provider):
        facts = provider.get_company_facts("AAPL")
        values = provider.extract_gaap_concept(facts, "NetIncomeLoss", form="10-K")
        assert len(values) > 0
        assert all(entry["form"] == "10-K" for entry in values)

    def test_get_detailed_financials_income_statement(self, provider):
        result = provider.get_detailed_financials("AAPL")
        assert "Income Statement" in result
        assert len(result["Income Statement"]) > 0

    def test_get_recent_filings_aapl(self, provider):
        filings = provider.get_recent_filings("AAPL", count=5)
        assert len(filings) == 5
        assert all("form" in f and "date" in f for f in filings)

    def test_get_insider_transactions_aapl(self, provider):
        txns = provider.get_insider_transactions("AAPL")
        # Should contain some Form 4 filings
        assert isinstance(txns, list)
        if txns:
            assert txns[0]["form"] in ("3", "4", "5")


# ── MFAPI (Indian Mutual Funds) ───────────────────────────────────────────────

class TestMfapiIntegration:
    @pytest.fixture(scope="class")
    def provider(self):
        from dashboard.providers.mfapi_provider import MfapiProvider
        return MfapiProvider()

    def test_search_funds_returns_results(self, provider):
        results = provider.search_funds("SBI Small Cap")
        assert isinstance(results, list)
        assert len(results) > 0

    def test_get_fund_detail_sbi_small_cap(self, provider):
        # SBI Small Cap Fund - Direct Plan - Growth
        detail = provider.get_fund_detail("125497")
        assert detail is not None
        assert "meta" in detail
        assert "data" in detail
        assert len(detail["data"]) > 0

    def test_calculate_returns_from_live_data(self, provider):
        detail = provider.get_fund_detail("125497")
        nav_data = detail["data"]
        returns = provider._calculate_returns(nav_data)
        assert "1Y" in returns or "6M" in returns  # At least some periods available
        if "1Y" in returns:
            assert isinstance(returns["1Y"]["return_pct"], float)

    def test_nav_series_returns_floats(self, provider):
        detail = provider.get_fund_detail("125497")
        nav_data = detail["data"]
        series = provider._nav_series(nav_data, days=365)
        assert len(series) > 0
        assert all(isinstance(v, float) for v in series)


# ── Full Stack (Service Layer) ────────────────────────────────────────────────

class TestStockServiceIntegration:
    @pytest.fixture(scope="class")
    def service(self):
        from dashboard.services.stock_service import StockAnalysisService
        return StockAnalysisService()

    def test_get_info_and_key_ratios_aapl(self, service):
        from dashboard.models import KeyRatios
        info = service.get_info("AAPL")
        ratios = service.get_key_ratios(info)
        assert isinstance(ratios, KeyRatios)
        # At least some ratios should be populated
        populated = [v for v in ratios.to_display_dict().values() if v is not None]
        assert len(populated) > 5

    def test_get_comparison_data_returns_typed_objects(self, service):
        from dashboard.models import ComparisonData
        result = service.get_comparison_data(["AAPL", "MSFT"])
        assert len(result) >= 1
        assert all(isinstance(cd, ComparisonData) for cd in result)

    def test_build_export_data_has_required_keys(self, service):
        data = service.build_export_data("AAPL")
        assert "info" in data
        assert "ratios" in data
        assert "price_history" in data
