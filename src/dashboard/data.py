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
