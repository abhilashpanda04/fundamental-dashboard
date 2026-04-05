"""SEC EDGAR data provider — concrete Strategy implementation.

All APIs are free; only a User-Agent header with a contact e-mail is
required by the SEC fair-access policy.  Set SEC_EDGAR_EMAIL in your
environment to customise it.
"""

from __future__ import annotations

import logging
from functools import lru_cache

import requests

from dashboard.config import config
from dashboard.exceptions import CIKNotFoundError, DataFetchError

logger = logging.getLogger(__name__)

# ── GAAP concept definitions ──────────────────────────────────────────────────
# Organised into display categories for the detailed financials view.
GAAP_CONCEPTS: dict[str, list[tuple[str, str]]] = {
    "Income Statement": [
        ("Revenue", "RevenueFromContractWithCustomerExcludingAssessedTax"),
        ("Revenue (Alt)", "Revenues"),
        ("Cost of Revenue", "CostOfGoodsAndServicesSold"),
        ("Gross Profit", "GrossProfit"),
        ("R&D Expense", "ResearchAndDevelopmentExpense"),
        ("SG&A Expense", "SellingGeneralAndAdministrativeExpense"),
        ("Operating Income", "OperatingIncomeLoss"),
        ("Interest Income", "InvestmentIncomeInterest"),
        ("Interest Expense", "InterestExpense"),
        ("Income Tax Expense", "IncomeTaxExpenseBenefit"),
        ("Net Income", "NetIncomeLoss"),
        ("EPS (Basic)", "EarningsPerShareBasic"),
        ("EPS (Diluted)", "EarningsPerShareDiluted"),
    ],
    "Comprehensive Income": [
        ("Net Income", "NetIncomeLoss"),
        ("OCI (Net)", "OtherComprehensiveIncomeLossNetOfTaxPortionAttributableToParent"),
        ("OCI - Securities", "OtherComprehensiveIncomeLossAvailableForSaleSecuritiesAdjustmentNetOfTax"),
        ("OCI - Derivatives", "OtherComprehensiveIncomeLossDerivativesQualifyingAsHedgesNetOfTax"),
        ("OCI - FX", "OtherComprehensiveIncomeLossForeignCurrencyTransactionAndTranslationAdjustmentNetOfTax"),
        ("Comprehensive Income", "ComprehensiveIncomeNetOfTax"),
        ("AOCI Balance", "AccumulatedOtherComprehensiveIncomeLossNetOfTax"),
    ],
    "Balance Sheet (Assets)": [
        ("Cash & Equivalents", "CashAndCashEquivalentsAtCarryingValue"),
        ("Short-term Investments", "ShortTermInvestments"),
        ("Marketable Securities (Current)", "AvailableForSaleSecuritiesDebtSecuritiesCurrent"),
        ("Accounts Receivable", "AccountsReceivableNetCurrent"),
        ("Inventory", "InventoryNet"),
        ("Other Current Assets", "OtherAssetsCurrent"),
        ("Total Current Assets", "AssetsCurrent"),
        ("Marketable Securities (Non-current)", "AvailableForSaleSecuritiesDebtSecuritiesNoncurrent"),
        ("PP&E (Net)", "PropertyPlantAndEquipmentNet"),
        ("Goodwill", "Goodwill"),
        ("Intangible Assets (Net)", "FiniteLivedIntangibleAssetsNet"),
        ("Other Non-current Assets", "OtherAssetsNoncurrent"),
        ("Total Assets", "Assets"),
    ],
    "Balance Sheet (Liabilities & Equity)": [
        ("Accounts Payable", "AccountsPayableCurrent"),
        ("Deferred Revenue (Current)", "DeferredRevenueCurrent"),
        ("Commercial Paper", "CommercialPaper"),
        ("Current Portion LT Debt", "LongTermDebtCurrent"),
        ("Other Current Liabilities", "OtherLiabilitiesCurrent"),
        ("Total Current Liabilities", "LiabilitiesCurrent"),
        ("Long-term Debt", "LongTermDebtNoncurrent"),
        ("Deferred Revenue (Non-current)", "DeferredRevenueNoncurrent"),
        ("Other Non-current Liabilities", "OtherLiabilitiesNoncurrent"),
        ("Total Liabilities", "Liabilities"),
        ("Common Stock + APIC", "CommonStocksIncludingAdditionalPaidInCapital"),
        ("Retained Earnings", "RetainedEarningsAccumulatedDeficit"),
        ("AOCI", "AccumulatedOtherComprehensiveIncomeLossNetOfTax"),
        ("Stockholders Equity", "StockholdersEquity"),
        ("Total Liabilities & Equity", "LiabilitiesAndStockholdersEquity"),
    ],
    "Cash Flow": [
        ("Net Income", "NetIncomeLoss"),
        ("D&A", "DepreciationDepletionAndAmortization"),
        ("Stock-Based Compensation", "ShareBasedCompensation"),
        ("Operating Cash Flow", "NetCashProvidedByOperatingActivities"),
        ("CapEx", "PaymentsToAcquirePropertyPlantAndEquipment"),
        ("Purchases of Investments", "PaymentsToAcquireAvailableForSaleSecuritiesDebt"),
        ("Proceeds from Investments", "ProceedsFromSaleOfAvailableForSaleSecuritiesDebt"),
        ("Financing Cash Flow", "NetCashProvidedByFinancingActivities"),
        ("Dividends Paid", "PaymentsOfDividends"),
        ("Share Repurchases", "PaymentsForRepurchaseOfCommonStock"),
        ("Debt Issued", "ProceedsFromIssuanceOfLongTermDebt"),
        ("Debt Repaid", "RepaymentsOfLongTermDebt"),
    ],
    "Per Share & Shares": [
        ("EPS (Basic)", "EarningsPerShareBasic"),
        ("EPS (Diluted)", "EarningsPerShareDiluted"),
        ("Dividend Per Share (Declared)", "CommonStockDividendsPerShareDeclared"),
        ("Dividend Per Share (Paid)", "CommonStockDividendsPerShareCashPaid"),
        ("Shares Outstanding", "CommonStockSharesOutstanding"),
        ("Shares Issued", "CommonStockSharesIssued"),
        ("Shares Authorized", "CommonStockSharesAuthorized"),
    ],
    "Debt Maturity Schedule": [
        ("Total LT Debt (Gross)", "DebtInstrumentCarryingAmount"),
        ("Due Year 1", "LongTermDebtMaturitiesRepaymentsOfPrincipalInNextTwelveMonths"),
        ("Due Year 2", "LongTermDebtMaturitiesRepaymentsOfPrincipalInYearTwo"),
        ("Due Year 3", "LongTermDebtMaturitiesRepaymentsOfPrincipalInYearThree"),
        ("Due Year 4", "LongTermDebtMaturitiesRepaymentsOfPrincipalInYearFour"),
        ("Due Year 5", "LongTermDebtMaturitiesRepaymentsOfPrincipalInYearFive"),
        ("Due After Year 5", "LongTermDebtMaturitiesRepaymentsOfPrincipalAfterYearFive"),
    ],
}


class SecEdgarProvider:
    """Fetches SEC EDGAR data: XBRL financials, filings, and insider transactions."""

    _BASE = "https://data.sec.gov"
    _TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"

    # ── CIK resolution ────────────────────────────────────────────────────────

    @lru_cache(maxsize=1)  # noqa: B019
    def _load_ticker_map(self) -> dict[str, str]:
        """Fetch and cache the SEC ticker → CIK mapping.

        The file is ~2 MB and only needs to be downloaded once per session.
        """
        try:
            r = requests.get(
                self._TICKERS_URL,
                headers=config.sec_headers,
                timeout=config.request_timeout,
            )
            r.raise_for_status()
            data = r.json()
            return {v["ticker"].upper(): str(v["cik_str"]).zfill(10) for v in data.values()}
        except Exception as exc:
            raise DataFetchError("SEC EDGAR", f"Failed to load ticker map: {exc}") from exc

    def get_cik(self, symbol: str) -> str:
        """Resolve a ticker to its padded 10-digit CIK.

        Raises:
            CIKNotFoundError: When the ticker is not in the SEC mapping.
            DataFetchError: On network failures.
        """
        ticker_map = self._load_ticker_map()
        cik = ticker_map.get(symbol.upper())
        if not cik:
            raise CIKNotFoundError(symbol)
        return cik

    # ── Company facts (XBRL) ─────────────────────────────────────────────────

    def get_company_facts(self, symbol: str) -> dict:
        """Return all XBRL financial facts for *symbol*.

        Raises:
            CIKNotFoundError: When the ticker is unknown.
            DataFetchError: On network / parse failures.
        """
        cik = self.get_cik(symbol)
        url = f"{self._BASE}/api/xbrl/companyfacts/CIK{cik}.json"
        try:
            r = requests.get(url, headers=config.sec_headers, timeout=config.request_timeout)
            r.raise_for_status()
            return r.json()
        except Exception as exc:
            raise DataFetchError("SEC EDGAR", f"Failed to fetch company facts: {exc}") from exc

    def extract_gaap_concept(
        self,
        facts: dict,
        concept: str,
        form: str = "10-K",
    ) -> list[dict]:
        """Extract annual (10-K) values for a single GAAP concept.

        Args:
            facts: Output of ``get_company_facts``.
            concept: US-GAAP concept name (e.g. ``"NetIncomeLoss"``).
            form: SEC form type filter (default ``"10-K"`` for annual).

        Returns:
            Chronologically sorted list of value dicts.
        """
        gaap = facts.get("facts", {}).get("us-gaap", {})
        concept_data = gaap.get(concept, {})
        if not concept_data:
            return []

        units = concept_data.get("units", {})
        values = (
            units.get("USD")
            or units.get("USD/shares")
            or units.get("shares")
            or next(iter(units.values()), [])
        )

        seen: set[tuple] = set()
        filtered: list[dict] = []
        for entry in values:
            if entry.get("form") == form:
                key = (entry.get("end"), entry.get("fy"))
                if key not in seen:
                    seen.add(key)
                    filtered.append(entry)

        filtered.sort(key=lambda x: x.get("end", ""))
        return filtered

    def get_detailed_financials(self, symbol: str) -> dict:
        """Return structured financial data from XBRL, organised by category.

        Returns an empty dict when the company has no SEC filings.
        """
        try:
            facts = self.get_company_facts(symbol)
        except (CIKNotFoundError, DataFetchError) as exc:
            logger.warning("SEC EDGAR: %s", exc)
            return {}

        result: dict[str, dict] = {}
        for category, items in GAAP_CONCEPTS.items():
            category_data: dict[str, list] = {}
            for display_name, concept_name in items:
                values = self.extract_gaap_concept(facts, concept_name)
                if values:
                    category_data[display_name] = values
            if category_data:
                result[category] = category_data

        return result

    # ── Filings ───────────────────────────────────────────────────────────────

    def get_recent_filings(self, symbol: str, count: int = 20) -> list[dict]:
        """Return the most recent SEC filings for *symbol*.

        Raises:
            CIKNotFoundError, DataFetchError on failures.
        """
        cik = self.get_cik(symbol)
        url = f"{self._BASE}/submissions/CIK{cik}.json"

        try:
            r = requests.get(url, headers=config.sec_headers, timeout=config.request_timeout)
            r.raise_for_status()
            data = r.json()
        except Exception as exc:
            raise DataFetchError("SEC EDGAR", f"Failed to fetch filings: {exc}") from exc

        recent = data.get("filings", {}).get("recent", {})
        forms = recent.get("form", [])
        dates = recent.get("filingDate", [])
        accessions = recent.get("accessionNumber", [])
        documents = recent.get("primaryDocument", [])
        descriptions = recent.get("primaryDocDescription", [])

        filings: list[dict] = []
        for i in range(min(count, len(forms))):
            accession_clean = accessions[i].replace("-", "")
            cik_int = cik.lstrip("0")
            url_filing = (
                f"https://www.sec.gov/Archives/edgar/data"
                f"/{cik_int}/{accession_clean}/{documents[i]}"
            )
            filings.append(
                {
                    "form": forms[i],
                    "date": dates[i],
                    "accession": accessions[i],
                    "document": documents[i],
                    "description": descriptions[i] if i < len(descriptions) else "",
                    "url": url_filing,
                }
            )

        return filings

    def get_insider_transactions(self, symbol: str) -> list[dict]:
        """Return Form 3, 4, and 5 insider transaction filings for *symbol*."""
        try:
            filings = self.get_recent_filings(symbol, count=50)
        except (CIKNotFoundError, DataFetchError) as exc:
            logger.warning("Insider transactions: %s", exc)
            return []
        return [f for f in filings if f["form"] in ("3", "4", "5")]
