from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
import pandas as pd

@dataclass
class DividendAnalysis:
    symbol: str
    name: str = ""
    current_price: Optional[float] = None
    annual_dividend: Optional[float] = None
    dividend_yield: Optional[float] = None
    payout_ratio: Optional[float] = None
    ex_dividend_date: Optional[str] = None
    dividend_history: list[dict] = field(default_factory=list)
    years_of_data: int = 0
    dividend_cagr_3y: Optional[float] = None
    dividend_cagr_5y: Optional[float] = None
    dividend_cagr_10y: Optional[float] = None
    consecutive_years_growth: int = 0
    is_dividend_aristocrat: bool = False
    yield_on_cost_5y: Optional[float] = None
    drip_growth_5y: Optional[float] = None
    rating: str = "N/A"
    highlights: list[str] = field(default_factory=list)
    concerns: list[str] = field(default_factory=list)

def analyze_dividends(symbol: str, stock=None) -> DividendAnalysis:
    import finscope
    if stock is None: stock = finscope.stock(symbol)
    info = stock.info
    res = DividendAnalysis(symbol.upper(), info.get("shortName"), info.get("currentPrice"), 
                           info.get("dividendRate"), info.get("dividendYield"), info.get("payoutRatio"))
    try:
        import yfinance as yf
        ticker = yf.Ticker(symbol)
        divs = ticker.dividends
        if not divs.empty:
            res.dividend_history = [{"date": str(d)[:10], "amount": float(v)} for d,v in divs.items()]
            annual = divs.groupby(divs.index.year).sum()
            res.years_of_data = len(annual)
            res.rating = "Reliable" if len(annual) > 5 else "Minimal"
            res.rating = "Non-Payer" if divs.empty else res.rating
        else: res.rating = "Non-Payer"
    except: res.rating = "Non-Payer"
    return res
