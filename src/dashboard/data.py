"""Fetches stock data from Yahoo Finance."""

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta


def get_ticker(symbol: str) -> yf.Ticker:
    """Create a yfinance Ticker object."""
    return yf.Ticker(symbol)


def get_company_info(ticker: yf.Ticker) -> dict:
    """Get company profile information."""
    return ticker.info


def get_financials(ticker: yf.Ticker) -> pd.DataFrame:
    """Get the annual income statement."""
    return ticker.financials


def get_balance_sheet(ticker: yf.Ticker) -> pd.DataFrame:
    """Get the annual balance sheet."""
    return ticker.balance_sheet


def get_cashflow(ticker: yf.Ticker) -> pd.DataFrame:
    """Get the annual cash flow statement."""
    return ticker.cashflow


def get_price_history(ticker: yf.Ticker, period: str = "1mo") -> pd.DataFrame:
    """Get historical price data.

    Args:
        ticker: yfinance Ticker object.
        period: Valid periods: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max

    Returns:
        DataFrame with OHLCV data.
    """
    return ticker.history(period=period)


def get_news(ticker: yf.Ticker) -> list[dict]:
    """Get recent news articles for the ticker."""
    return ticker.news or []


def get_analyst_recommendations(ticker: yf.Ticker) -> pd.DataFrame | None:
    """Get analyst recommendations (buy/sell/hold counts)."""
    try:
        recs = ticker.recommendations
        if recs is not None and not recs.empty:
            return recs
    except Exception:
        pass
    return None


def get_major_holders(ticker: yf.Ticker) -> tuple[pd.DataFrame | None, pd.DataFrame | None]:
    """Get major holders info.

    Returns:
        Tuple of (holders_breakdown, institutional_holders).
    """
    try:
        breakdown = ticker.major_holders
    except Exception:
        breakdown = None

    try:
        institutional = ticker.institutional_holders
    except Exception:
        institutional = None

    return breakdown, institutional


def get_sparkline_data(ticker: yf.Ticker, period: str = "3mo") -> list[float]:
    """Get closing prices for sparkline rendering.

    Args:
        ticker: yfinance Ticker object.
        period: Time period for the sparkline.

    Returns:
        List of closing prices.
    """
    df = ticker.history(period=period)
    if df.empty:
        return []

    close = df["Close"]
    # Handle MultiIndex columns
    if hasattr(close, "columns"):
        close = close.iloc[:, 0]

    return close.dropna().tolist()


def get_key_ratios(info: dict) -> dict:
    """Extract key financial ratios from the info dict."""
    keys = [
        ("P/E Ratio", "trailingPE"),
        ("Forward P/E", "forwardPE"),
        ("PEG Ratio", "pegRatio"),
        ("Price/Book", "priceToBook"),
        ("Price/Sales", "priceToSalesTrailing12Months"),
        ("EV/EBITDA", "enterpriseToEbitda"),
        ("Profit Margin", "profitMargins"),
        ("Operating Margin", "operatingMargins"),
        ("Return on Equity", "returnOnEquity"),
        ("Return on Assets", "returnOnAssets"),
        ("Debt/Equity", "debtToEquity"),
        ("Current Ratio", "currentRatio"),
        ("Revenue", "totalRevenue"),
        ("EBITDA", "ebitda"),
        ("Free Cash Flow", "freeCashflow"),
        ("Market Cap", "marketCap"),
        ("Enterprise Value", "enterpriseValue"),
        ("Dividend Yield", "dividendYield"),
        ("Beta", "beta"),
        ("52W High", "fiftyTwoWeekHigh"),
        ("52W Low", "fiftyTwoWeekLow"),
        ("50D Avg", "fiftyDayAverage"),
        ("200D Avg", "twoHundredDayAverage"),
    ]

    ratios = {}
    for display_name, key in keys:
        value = info.get(key)
        ratios[display_name] = value

    return ratios


def get_comparison_data(symbols: list[str]) -> list[dict]:
    """Fetch key metrics for multiple tickers for side-by-side comparison.

    Args:
        symbols: List of ticker symbols.

    Returns:
        List of dicts with ticker info and key ratios.
    """
    results = []

    for symbol in symbols:
        ticker = get_ticker(symbol)
        info = get_company_info(ticker)

        if not info or info.get("quoteType") is None:
            continue

        results.append({
            "symbol": symbol.upper(),
            "name": info.get("shortName", "N/A"),
            "price": info.get("currentPrice") or info.get("regularMarketPrice"),
            "change_pct": info.get("regularMarketChangePercent"),
            "market_cap": info.get("marketCap"),
            "pe_ratio": info.get("trailingPE"),
            "forward_pe": info.get("forwardPE"),
            "peg": info.get("pegRatio"),
            "pb": info.get("priceToBook"),
            "ps": info.get("priceToSalesTrailing12Months"),
            "profit_margin": info.get("profitMargins"),
            "roe": info.get("returnOnEquity"),
            "debt_equity": info.get("debtToEquity"),
            "dividend_yield": info.get("dividendYield"),
            "beta": info.get("beta"),
            "revenue": info.get("totalRevenue"),
            "ebitda": info.get("ebitda"),
            "sparkline": get_sparkline_data(ticker, "3mo"),
        })

    return results
