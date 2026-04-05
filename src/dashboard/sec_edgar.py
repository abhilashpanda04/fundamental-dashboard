"""Fetches data from SEC EDGAR APIs.

SEC EDGAR is the official source for all US public company filings.
All APIs are completely free — no API key required. Only needs a
User-Agent header with a contact email per SEC fair access policy.

Data available:
- Company facts (XBRL): 500+ financial line items with full history
- Recent filings: 10-K, 10-Q, 8-K, proxy statements, insider trades
- Insider transactions: Form 4 filings
"""

import requests
import json
import os
import logging
from functools import lru_cache

logger = logging.getLogger(__name__)

# SEC requires a User-Agent with contact info per fair access policy.
# Set SEC_EDGAR_EMAIL env var, or it falls back to a generic identifier.
USER_EMAIL = os.environ.get("SEC_EDGAR_EMAIL", "fundamental-dashboard-user@example.com")
USER_AGENT = f"FundamentalDashboard {USER_EMAIL}"
HEADERS = {"User-Agent": USER_AGENT, "Accept-Encoding": "gzip, deflate"}

# ──────────────────────────────────────────────────────────────
# CIK Lookup
# ──────────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _load_ticker_map() -> dict:
    """Load the SEC ticker-to-CIK mapping (cached)."""
    url = "https://www.sec.gov/files/company_tickers.json"
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        r.raise_for_status()
        data = r.json()
        # Build ticker -> CIK map
        return {v["ticker"].upper(): str(v["cik_str"]).zfill(10) for v in data.values()}
    except Exception as e:
        logger.warning(f"Failed to load SEC ticker map: {e}")
        return {}


def get_cik(symbol: str) -> str | None:
    """Look up the SEC CIK number for a ticker symbol."""
    ticker_map = _load_ticker_map()
    return ticker_map.get(symbol.upper())


# ──────────────────────────────────────────────────────────────
# Company Facts (XBRL)
# ──────────────────────────────────────────────────────────────

def get_company_facts(symbol: str) -> dict | None:
    """Fetch all XBRL financial facts for a company from SEC EDGAR.

    This returns 500+ financial concepts (Revenue, NetIncome, Assets, etc.)
    with full historical values from every 10-K and 10-Q filing.

    Args:
        symbol: Stock ticker symbol.

    Returns:
        Dict with 'entityName' and 'facts' containing US-GAAP and DEI data.
    """
    cik = get_cik(symbol)
    if not cik:
        logger.warning(f"Could not find CIK for {symbol}")
        return None

    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"

    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        logger.warning(f"Failed to fetch company facts for {symbol}: {e}")
        return None


def extract_gaap_concept(facts: dict, concept: str, form: str = "10-K") -> list[dict]:
    """Extract a specific GAAP concept's historical values.

    Args:
        facts: Company facts dict from get_company_facts().
        concept: US-GAAP concept name (e.g., 'Revenues', 'NetIncomeLoss').
        form: Filing form to filter by ('10-K' for annual, '10-Q' for quarterly).

    Returns:
        List of dicts with 'end', 'val', 'fy', 'fp' keys, sorted by date.
    """
    gaap = facts.get("facts", {}).get("us-gaap", {})
    concept_data = gaap.get(concept, {})

    if not concept_data:
        return []

    # Get USD-denominated values
    units = concept_data.get("units", {})
    values = units.get("USD", []) or units.get("USD/shares", []) or units.get("shares", [])

    if not values:
        # Try the first available unit
        for unit_key, unit_vals in units.items():
            values = unit_vals
            break

    # Filter by form type and deduplicate
    filtered = []
    seen = set()
    for entry in values:
        if entry.get("form") == form:
            key = (entry.get("end"), entry.get("fy"))
            if key not in seen:
                seen.add(key)
                filtered.append(entry)

    # Sort by end date
    filtered.sort(key=lambda x: x.get("end", ""))
    return filtered


def get_detailed_financials(symbol: str) -> dict:
    """Get detailed financial data from SEC EDGAR XBRL.

    Returns a dict organized by category with historical values.
    """
    facts = get_company_facts(symbol)
    if not facts:
        return {}

    # Key financial concepts organized into detailed statement categories
    concepts = {
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
            ("Other Comprehensive Income (Net)", "OtherComprehensiveIncomeLossNetOfTaxPortionAttributableToParent"),
            ("OCI - Securities", "OtherComprehensiveIncomeLossAvailableForSaleSecuritiesAdjustmentNetOfTax"),
            ("OCI - Derivatives/Hedges", "OtherComprehensiveIncomeLossDerivativesQualifyingAsHedgesNetOfTax"),
            ("OCI - Foreign Currency", "OtherComprehensiveIncomeLossForeignCurrencyTransactionAndTranslationAdjustmentNetOfTax"),
            ("Comprehensive Income (Total)", "ComprehensiveIncomeNetOfTax"),
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
            ("Property, Plant & Equipment (Net)", "PropertyPlantAndEquipmentNet"),
            ("Goodwill", "Goodwill"),
            ("Intangible Assets (Net)", "FiniteLivedIntangibleAssetsNet"),
            ("Other Non-current Assets", "OtherAssetsNoncurrent"),
            ("Total Assets", "Assets"),
        ],
        "Balance Sheet (Liabilities & Equity)": [
            ("Accounts Payable", "AccountsPayableCurrent"),
            ("Deferred Revenue (Current)", "DeferredRevenueCurrent"),
            ("Commercial Paper", "CommercialPaper"),
            ("Current Portion of LT Debt", "LongTermDebtCurrent"),
            ("Other Current Liabilities", "OtherLiabilitiesCurrent"),
            ("Total Current Liabilities", "LiabilitiesCurrent"),
            ("Long-term Debt", "LongTermDebtNoncurrent"),
            ("Deferred Revenue (Non-current)", "DeferredRevenueNoncurrent"),
            ("Other Non-current Liabilities", "OtherLiabilitiesNoncurrent"),
            ("Total Liabilities", "Liabilities"),
            ("Common Stock", "CommonStocksIncludingAdditionalPaidInCapital"),
            ("Retained Earnings", "RetainedEarningsAccumulatedDeficit"),
            ("AOCI", "AccumulatedOtherComprehensiveIncomeLossNetOfTax"),
            ("Stockholders Equity", "StockholdersEquity"),
            ("Total Liabilities & Equity", "LiabilitiesAndStockholdersEquity"),
        ],
        "Cash Flow": [
            ("Net Income", "NetIncomeLoss"),
            ("Depreciation & Amortization", "DepreciationDepletionAndAmortization"),
            ("Stock-Based Compensation", "ShareBasedCompensation"),
            ("Operating Cash Flow", "NetCashProvidedByOperatingActivities"),
            ("CapEx", "PaymentsToAcquirePropertyPlantAndEquipment"),
            ("Purchases of Investments", "PaymentsToAcquireAvailableForSaleSecuritiesDebt"),
            ("Proceeds from Investments", "ProceedsFromSaleOfAvailableForSaleSecuritiesDebt"),
            ("Investing Cash Flow", "NetCashProvidedByFinancingActivities"),
            ("Dividends Paid", "PaymentsOfDividends"),
            ("Share Repurchases", "PaymentsForRepurchaseOfCommonStock"),
            ("Debt Issued", "ProceedsFromIssuanceOfLongTermDebt"),
            ("Debt Repaid", "RepaymentsOfLongTermDebt"),
        ],
        "Per Share & Shares": [
            ("EPS (Basic)", "EarningsPerShareBasic"),
            ("EPS (Diluted)", "EarningsPerShareDiluted"),
            ("Dividend Per Share", "CommonStockDividendsPerShareDeclared"),
            ("Dividend Per Share (Paid)", "CommonStockDividendsPerShareCashPaid"),
            ("Shares Outstanding", "CommonStockSharesOutstanding"),
            ("Shares Issued", "CommonStockSharesIssued"),
            ("Shares Authorized", "CommonStockSharesAuthorized"),
        ],
        "Debt Maturity Schedule": [
            ("Total Long-term Debt (Gross)", "DebtInstrumentCarryingAmount"),
            ("Due Year 1", "LongTermDebtMaturitiesRepaymentsOfPrincipalInNextTwelveMonths"),
            ("Due Year 2", "LongTermDebtMaturitiesRepaymentsOfPrincipalInYearTwo"),
            ("Due Year 3", "LongTermDebtMaturitiesRepaymentsOfPrincipalInYearThree"),
            ("Due Year 4", "LongTermDebtMaturitiesRepaymentsOfPrincipalInYearFour"),
            ("Due Year 5", "LongTermDebtMaturitiesRepaymentsOfPrincipalInYearFive"),
            ("Due After Year 5", "LongTermDebtMaturitiesRepaymentsOfPrincipalAfterYearFive"),
        ],
    }

    result = {}
    for category, items in concepts.items():
        category_data = {}
        for display_name, concept_name in items:
            values = extract_gaap_concept(facts, concept_name)
            if values:
                category_data[display_name] = values
        if category_data:
            result[category] = category_data

    return result


# ──────────────────────────────────────────────────────────────
# SEC Filings (10-K, 10-Q, 8-K, etc.)
# ──────────────────────────────────────────────────────────────

def get_recent_filings(symbol: str, count: int = 20) -> list[dict]:
    """Get recent SEC filings for a company.

    Args:
        symbol: Stock ticker symbol.
        count: Number of filings to return.

    Returns:
        List of dicts with form, filingDate, accessionNumber, primaryDocument.
    """
    cik = get_cik(symbol)
    if not cik:
        return []

    url = f"https://data.sec.gov/submissions/CIK{cik}.json"

    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        logger.warning(f"Failed to fetch filings for {symbol}: {e}")
        return []

    recent = data.get("filings", {}).get("recent", {})

    forms = recent.get("form", [])
    dates = recent.get("filingDate", [])
    accessions = recent.get("accessionNumber", [])
    documents = recent.get("primaryDocument", [])
    descriptions = recent.get("primaryDocDescription", [])

    filings = []
    for i in range(min(count, len(forms))):
        accession_clean = accessions[i].replace("-", "")
        filing_url = f"https://www.sec.gov/Archives/edgar/data/{cik.lstrip('0')}/{accession_clean}/{documents[i]}"

        filings.append({
            "form": forms[i],
            "date": dates[i],
            "accession": accessions[i],
            "document": documents[i],
            "description": descriptions[i] if i < len(descriptions) else "",
            "url": filing_url,
        })

    return filings


def get_insider_transactions(symbol: str) -> list[dict]:
    """Get recent insider transactions (Form 4 filings).

    Returns:
        List of insider transaction filings.
    """
    filings = get_recent_filings(symbol, count=50)
    return [f for f in filings if f["form"] in ("4", "3", "5")]
