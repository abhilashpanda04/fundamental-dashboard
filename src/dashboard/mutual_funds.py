"""Mutual Fund data fetcher from multiple free sources.

Data Sources:
- India: MFAPI.in (37,500+ SEBI-registered funds, completely free)
- US & Global ETFs: Yahoo Finance (free via yfinance)
"""

import requests
import logging
from datetime import datetime, timedelta
from functools import lru_cache

import yfinance as yf
import pandas as pd

logger = logging.getLogger(__name__)

MFAPI_BASE = "https://api.mfapi.in/mf"


# ──────────────────────────────────────────────────────────────
# India — MFAPI.in
# ──────────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _get_all_india_funds() -> list[dict]:
    """Fetch the complete list of Indian mutual funds (cached)."""
    try:
        r = requests.get(MFAPI_BASE, timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        logger.warning(f"Failed to fetch Indian fund list: {e}")
        return []


def search_india_funds(query: str) -> list[dict]:
    """Search Indian mutual funds by name.

    Args:
        query: Search string (e.g., 'SBI Small Cap', 'HDFC Mid Cap')

    Returns:
        List of matching fund dicts with schemeCode and schemeName.
    """
    try:
        r = requests.get(f"{MFAPI_BASE}/search?q={query}", timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception:
        # Fallback: local search from cached list
        funds = _get_all_india_funds()
        q = query.lower()
        return [f for f in funds if q in f["schemeName"].lower()][:20]


def get_india_fund_detail(scheme_code: str | int) -> dict | None:
    """Fetch full NAV history and metadata for an Indian mutual fund.

    Args:
        scheme_code: AMFI scheme code (e.g., 125497 for SBI Small Cap Direct Growth)

    Returns:
        Dict with 'meta' and 'data' (list of NAV records).
    """
    try:
        r = requests.get(f"{MFAPI_BASE}/{scheme_code}", timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        logger.warning(f"Failed to fetch fund {scheme_code}: {e}")
        return None


def calculate_india_fund_returns(nav_data: list[dict]) -> dict:
    """Calculate point-to-point returns for different time periods.

    Args:
        nav_data: List of {'date': 'DD-MM-YYYY', 'nav': 'value'} from MFAPI.

    Returns:
        Dict mapping period labels to (return_pct, start_nav, start_date).
    """
    if not nav_data:
        return {}

    def parse_date(d: str) -> datetime:
        return datetime.strptime(d, "%d-%m-%Y")

    current_nav = float(nav_data[0]["nav"])
    current_date = parse_date(nav_data[0]["date"])

    def find_closest(target: datetime) -> tuple[float, datetime] | tuple[None, None]:
        for entry in nav_data:
            d = parse_date(entry["date"])
            if d <= target:
                return float(entry["nav"]), d
        return None, None

    periods = {
        "1W": 7,
        "1M": 30,
        "3M": 90,
        "6M": 180,
        "1Y": 365,
        "2Y": 365 * 2,
        "3Y": 365 * 3,
        "5Y": 365 * 5,
        "10Y": 365 * 10,
    }

    returns = {}
    for label, days in periods.items():
        target = current_date - timedelta(days=days)
        past_nav, past_date = find_closest(target)
        if past_nav:
            pct = ((current_nav - past_nav) / past_nav) * 100
            returns[label] = {
                "return_pct": pct,
                "start_nav": past_nav,
                "start_date": past_date.strftime("%d-%m-%Y"),
                "current_nav": current_nav,
            }

    return returns


def get_india_fund_nav_series(nav_data: list[dict], days: int = 365) -> list[float]:
    """Extract NAV values as a list for sparkline rendering.

    Args:
        nav_data: Full NAV history from MFAPI.
        days: Number of past days to include.

    Returns:
        Ordered list of NAV floats (oldest to newest).
    """
    if not nav_data:
        return []

    cutoff = datetime.now() - timedelta(days=days)
    values = []

    for entry in reversed(nav_data):
        try:
            d = datetime.strptime(entry["date"], "%d-%m-%Y")
            if d >= cutoff:
                values.append(float(entry["nav"]))
        except Exception:
            continue

    return values


# ──────────────────────────────────────────────────────────────
# US & Global — Yahoo Finance
# ──────────────────────────────────────────────────────────────

# Curated list of popular funds by region
POPULAR_FUNDS = {
    "US": [
        ("VFIAX", "Vanguard 500 Index (Admiral)"),
        ("FXAIX", "Fidelity 500 Index"),
        ("VTSAX", "Vanguard Total Stock Market (Admiral)"),
        ("FCNTX", "Fidelity Contrafund"),
        ("AGTHX", "American Funds Growth Fund"),
        ("DODGX", "Dodge & Cox Stock"),
        ("PTTRX", "PIMCO Total Return"),
        ("VBTLX", "Vanguard Total Bond Market"),
    ],
    "Global ETF (LSE)": [
        ("VWRL.L", "Vanguard FTSE All-World"),
        ("SWDA.L", "iShares Core MSCI World"),
        ("EIMI.L", "iShares Core MSCI EM IMI"),
        ("CSPX.L", "iShares Core S&P 500"),
        ("VUSA.L", "Vanguard S&P 500 (GBP)"),
        ("AGGG.L", "iShares Core Global Agg Bond"),
        ("VFEM.L", "Vanguard FTSE Emerging Markets"),
        ("ISF.L",  "iShares Core FTSE 100"),
    ],
    "Asia Pacific ETF": [
        ("EWJ",   "iShares MSCI Japan"),
        ("EWY",   "iShares MSCI South Korea"),
        ("EWT",   "iShares MSCI Taiwan"),
        ("EWA",   "iShares MSCI Australia"),
        ("FXI",   "iShares China Large-Cap"),
        ("MCHI",  "iShares MSCI China"),
        ("INDA",  "iShares MSCI India"),
        ("VPL",   "Vanguard FTSE Pacific"),
    ],
    "European ETF": [
        ("EZU",   "iShares MSCI Eurozone"),
        ("EWG",   "iShares MSCI Germany"),
        ("EWQ",   "iShares MSCI France"),
        ("EWI",   "iShares MSCI Italy"),
        ("EWP",   "iShares MSCI Spain"),
        ("EWN",   "iShares MSCI Netherlands"),
        ("EWL",   "iShares MSCI Switzerland"),
    ],
    "Fixed Income / Bond ETF": [
        ("AGG",   "iShares Core US Aggregate Bond"),
        ("BND",   "Vanguard Total Bond Market"),
        ("TLT",   "iShares 20+ Year Treasury"),
        ("HYG",   "iShares iBoxx USD High Yield"),
        ("EMB",   "iShares JP Morgan USD EM Bond"),
        ("BNDX",  "Vanguard Total International Bond"),
    ],
}


def get_global_fund_info(symbol: str) -> dict | None:
    """Fetch mutual fund / ETF data from Yahoo Finance.

    Args:
        symbol: Yahoo Finance ticker (e.g., 'VFIAX', 'VWRL.L', 'INDA')

    Returns:
        Fund info dict with NAV, AUM, expense ratio, returns, etc.
    """
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info

        if not info or info.get("quoteType") is None:
            return None

        return info
    except Exception as e:
        logger.warning(f"Failed to fetch {symbol}: {e}")
        return None


def get_global_fund_returns(symbol: str) -> dict:
    """Calculate historical returns from Yahoo Finance price history.

    Args:
        symbol: Yahoo Finance ticker symbol.

    Returns:
        Dict mapping period labels to return percentages.
    """
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info

        returns = {
            "1Y (Reported)": info.get("ytdReturn"),
            "3Y (Reported)": info.get("threeYearAverageReturn"),
            "5Y (Reported)": info.get("fiveYearAverageReturn"),
        }

        # Calculate from price history
        hist = ticker.history(period="5y")
        if not hist.empty:
            close = hist["Close"].dropna()
            if hasattr(close, "columns"):
                close = close.iloc[:, 0]

            current = float(close.iloc[-1])

            def return_pct(days: int) -> float | None:
                cutoff = close.index[-1] - pd.Timedelta(days=days)
                past = close[close.index <= cutoff]
                if not past.empty:
                    return ((current - float(past.iloc[-1])) / float(past.iloc[-1])) * 100
                return None

            returns.update({
                "1W":  return_pct(7),
                "1M":  return_pct(30),
                "3M":  return_pct(90),
                "6M":  return_pct(180),
                "1Y":  return_pct(365),
                "3Y":  return_pct(365 * 3),
                "5Y":  return_pct(365 * 5),
            })

        return returns

    except Exception as e:
        logger.warning(f"Failed returns for {symbol}: {e}")
        return {}


def get_global_fund_sparkline(symbol: str, period: str = "1y") -> list[float]:
    """Get closing prices for sparkline rendering.

    Args:
        symbol: Yahoo Finance ticker.
        period: yfinance period string.

    Returns:
        List of closing prices (oldest to newest).
    """
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period=period)
        if hist.empty:
            return []
        close = hist["Close"].dropna()
        if hasattr(close, "columns"):
            close = close.iloc[:, 0]
        return [float(v) for v in close.tolist()]
    except Exception:
        return []


def get_popular_funds_snapshot(region: str) -> list[dict]:
    """Get a quick snapshot of all popular funds for a given region.

    Args:
        region: One of 'US', 'Global ETF (LSE)', 'Asia Pacific ETF', etc.

    Returns:
        List of fund snapshot dicts.
    """
    fund_list = POPULAR_FUNDS.get(region, [])
    results = []

    for symbol, description in fund_list:
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info

            nav = info.get("navPrice") or info.get("currentPrice") or info.get("previousClose")
            change = info.get("regularMarketChangePercent")
            assets = info.get("totalAssets")
            expense = info.get("annualReportExpenseRatio")
            ytd = info.get("ytdReturn")
            currency = info.get("currency", "USD")

            spark = get_global_fund_sparkline(symbol, "1y")

            results.append({
                "symbol": symbol,
                "description": description,
                "name": info.get("longName") or info.get("shortName") or description,
                "nav": nav,
                "change_pct": change,
                "currency": currency,
                "total_assets": assets,
                "expense_ratio": expense,
                "ytd_return": ytd,
                "sparkline": spark,
            })

        except Exception as e:
            logger.warning(f"Skipping {symbol}: {e}")

    return results
