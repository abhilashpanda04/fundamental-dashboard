"""Unit tests for ``SecEdgarProvider``."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from dashboard.exceptions import CIKNotFoundError, DataFetchError
from dashboard.providers.sec_edgar_provider import SecEdgarProvider


@pytest.fixture
def provider():
    # Create a fresh provider for each test (clears lru_cache side-effects)
    return SecEdgarProvider()


@pytest.fixture
def mock_ticker_map():
    return {"AAPL": "0000320193", "MSFT": "0000789019"}


@pytest.fixture
def minimal_facts():
    """Minimal SEC EDGAR XBRL facts structure."""
    return {
        "entityName": "Apple Inc.",
        "facts": {
            "us-gaap": {
                "NetIncomeLoss": {
                    "label": "Net Income (Loss)",
                    "units": {
                        "USD": [
                            {"end": "2023-09-30", "val": 96_995_000_000, "form": "10-K", "fy": 2023, "fp": "FY"},
                            {"end": "2022-09-30", "val": 99_803_000_000, "form": "10-K", "fy": 2022, "fp": "FY"},
                            {"end": "2021-09-30", "val": 94_680_000_000, "form": "10-K", "fy": 2021, "fp": "FY"},
                            # Quarterly entry — should be excluded when form="10-K"
                            {"end": "2023-06-30", "val": 19_881_000_000, "form": "10-Q", "fy": 2023, "fp": "Q3"},
                        ]
                    },
                }
            }
        },
    }


class TestGetCik:
    def test_returns_cik_for_known_ticker(self, provider, mock_ticker_map):
        with patch.object(provider, "_load_ticker_map", return_value=mock_ticker_map):
            cik = provider.get_cik("AAPL")
        assert cik == "0000320193"

    def test_case_insensitive(self, provider, mock_ticker_map):
        with patch.object(provider, "_load_ticker_map", return_value=mock_ticker_map):
            cik = provider.get_cik("aapl")
        assert cik == "0000320193"

    def test_raises_cik_not_found_for_unknown(self, provider, mock_ticker_map):
        with patch.object(provider, "_load_ticker_map", return_value=mock_ticker_map):
            with pytest.raises(CIKNotFoundError) as exc_info:
                provider.get_cik("UNKNOWN")
        assert "UNKNOWN" in str(exc_info.value)


class TestExtractGaapConcept:
    def test_extracts_10k_entries_only(self, provider, minimal_facts):
        results = provider.extract_gaap_concept(minimal_facts, "NetIncomeLoss", form="10-K")
        assert len(results) == 3  # Only 10-K entries
        for r in results:
            assert r["form"] == "10-K"

    def test_extracts_10q_entries_when_requested(self, provider, minimal_facts):
        results = provider.extract_gaap_concept(minimal_facts, "NetIncomeLoss", form="10-Q")
        assert len(results) == 1
        assert results[0]["form"] == "10-Q"

    def test_returns_empty_for_unknown_concept(self, provider, minimal_facts):
        results = provider.extract_gaap_concept(minimal_facts, "NonExistentConcept")
        assert results == []

    def test_sorted_by_end_date(self, provider, minimal_facts):
        results = provider.extract_gaap_concept(minimal_facts, "NetIncomeLoss")
        ends = [r["end"] for r in results]
        assert ends == sorted(ends)

    def test_deduplicates_same_end_fy(self, provider):
        """Duplicate (end, fy) entries must be deduplicated."""
        facts = {
            "facts": {
                "us-gaap": {
                    "Revenues": {
                        "units": {
                            "USD": [
                                {"end": "2023-09-30", "val": 100, "form": "10-K", "fy": 2023},
                                {"end": "2023-09-30", "val": 100, "form": "10-K", "fy": 2023},  # duplicate
                            ]
                        }
                    }
                }
            }
        }
        results = provider.extract_gaap_concept(facts, "Revenues")
        assert len(results) == 1

    def test_empty_facts_returns_empty(self, provider):
        results = provider.extract_gaap_concept({}, "NetIncomeLoss")
        assert results == []


class TestGetDetailedFinancials:
    def test_returns_dict_with_categories(self, provider, minimal_facts, mock_ticker_map):
        with (
            patch.object(provider, "_load_ticker_map", return_value=mock_ticker_map),
            patch.object(provider, "get_company_facts", return_value=minimal_facts),
        ):
            result = provider.get_detailed_financials("AAPL")

        # At minimum the Income Statement category should have Net Income
        assert isinstance(result, dict)
        assert "Income Statement" in result
        assert "Net Income" in result["Income Statement"]

    def test_returns_empty_dict_when_cik_not_found(self, provider):
        with patch.object(provider, "get_cik", side_effect=CIKNotFoundError("XYZ")):
            result = provider.get_detailed_financials("XYZ")
        assert result == {}

    def test_returns_empty_dict_on_data_fetch_error(self, provider, mock_ticker_map):
        with (
            patch.object(provider, "_load_ticker_map", return_value=mock_ticker_map),
            patch.object(
                provider,
                "get_company_facts",
                side_effect=DataFetchError("SEC EDGAR", "timeout"),
            ),
        ):
            result = provider.get_detailed_financials("AAPL")
        assert result == {}


class TestGetRecentFilings:
    def test_returns_list_of_dicts(self, provider, mock_ticker_map):
        submissions = {
            "filings": {
                "recent": {
                    "form": ["10-K", "10-Q"],
                    "filingDate": ["2023-11-03", "2023-08-04"],
                    "accessionNumber": ["0000320193-23-000106", "0000320193-23-000077"],
                    "primaryDocument": ["aapl-20230930.htm", "aapl-20230701.htm"],
                    "primaryDocDescription": ["Annual Report", "Quarterly Report"],
                }
            }
        }
        mock_response = MagicMock()
        mock_response.json.return_value = submissions
        mock_response.raise_for_status = MagicMock()

        with (
            patch.object(provider, "_load_ticker_map", return_value=mock_ticker_map),
            patch("dashboard.providers.sec_edgar_provider.requests.get", return_value=mock_response),
        ):
            filings = provider.get_recent_filings("AAPL", count=2)

        assert len(filings) == 2
        assert filings[0]["form"] == "10-K"
        assert filings[0]["date"] == "2023-11-03"

    def test_respects_count_limit(self, provider, mock_ticker_map):
        submissions = {
            "filings": {
                "recent": {
                    "form": ["10-K", "10-Q", "8-K"],
                    "filingDate": ["2023-11-03", "2023-08-04", "2023-06-01"],
                    "accessionNumber": ["acc1", "acc2", "acc3"],
                    "primaryDocument": ["doc1.htm", "doc2.htm", "doc3.htm"],
                    "primaryDocDescription": ["Annual", "Quarterly", "Current"],
                }
            }
        }
        mock_response = MagicMock()
        mock_response.json.return_value = submissions
        mock_response.raise_for_status = MagicMock()

        with (
            patch.object(provider, "_load_ticker_map", return_value=mock_ticker_map),
            patch("dashboard.providers.sec_edgar_provider.requests.get", return_value=mock_response),
        ):
            filings = provider.get_recent_filings("AAPL", count=1)

        assert len(filings) == 1


class TestGetInsiderTransactions:
    def test_filters_form_3_4_5(self, provider):
        all_filings = [
            {"form": "10-K", "date": "2023-11-03", "url": ""},
            {"form": "4",    "date": "2023-10-15", "url": ""},
            {"form": "10-Q", "date": "2023-08-04", "url": ""},
            {"form": "3",    "date": "2023-07-01", "url": ""},
            {"form": "5",    "date": "2023-02-01", "url": ""},
        ]
        with patch.object(provider, "get_recent_filings", return_value=all_filings):
            result = provider.get_insider_transactions("AAPL")

        assert len(result) == 3
        forms = {f["form"] for f in result}
        assert forms == {"3", "4", "5"}

    def test_returns_empty_on_error(self, provider):
        with patch.object(
            provider, "get_recent_filings", side_effect=CIKNotFoundError("XYZ")
        ):
            result = provider.get_insider_transactions("XYZ")
        assert result == []
