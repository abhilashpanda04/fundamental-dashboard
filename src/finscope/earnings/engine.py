from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
import pandas as pd

@dataclass
class EarningsSurprise:
    date: str
    reported_eps: Optional[float] = None
    estimated_eps: Optional[float] = None
    surprise_pct: Optional[float] = None
    beat: Optional[bool] = None

@dataclass
class EarningsAnalysis:
    symbol: str
    name: str = ""
    current_price: Optional[float] = None
    next_earnings_date: Optional[str] = None
    days_until_earnings: Optional[int] = None
    surprises: list[EarningsSurprise] = field(default_factory=list)
    quarters_tracked: int = 0
    eps_beat_rate: Optional[float] = None
    revenue_beat_rate: Optional[float] = None
    eps_trend: str = "N/A"
    revenue_trend: str = "N/A"
    earnings_growth_rate: Optional[float] = None
    revenue_growth_rate: Optional[float] = None
    rating: str = "N/A"
    highlights: list[str] = field(default_factory=list)
    concerns: list[str] = field(default_factory=list)

def analyze_earnings(symbol: str, stock=None) -> EarningsAnalysis:
    import finscope
    if stock is None: stock = finscope.stock(symbol)
    info = stock.info
    res = EarningsAnalysis(symbol.upper(), info.get("shortName"), info.get("currentPrice"))
    res.earnings_growth_rate, res.revenue_growth_rate = info.get("earningsGrowth"), info.get("revenueGrowth")
    res.eps_trend = "Growing" if (res.earnings_growth_rate or 0) > 0.1 else "Declining" if (res.earnings_growth_rate or 0) < -0.05 else "Flat"
    res.revenue_trend = "Growing" if (res.revenue_growth_rate or 0) > 0.1 else "Declining" if (res.revenue_growth_rate or 0) < -0.05 else "Flat"
    
    # Default rating based on trend
    if res.eps_trend == "Growing": res.rating = "Good"
    elif res.eps_trend == "Declining": res.rating = "Weak"
    else: res.rating = "Mixed"

    try:
        import yfinance as yf
        eh = yf.Ticker(symbol).earnings_history
        if eh is not None and not eh.empty:
            beats = 0
            for _, r in eh.iterrows():
                beat = (float(r["epsActual"]) >= float(r["epsEstimate"])) if (pd.notna(r.get("epsActual")) and pd.notna(r.get("epsEstimate"))) else None
                res.surprises.append(EarningsSurprise(str(r.name)[:10], r.get("epsActual"), r.get("epsEstimate"), r.get("surprisePercent"), beat))
                if beat: beats += 1
            res.eps_beat_rate = beats / len(eh); res.quarters_tracked = len(eh)
            res.rating = "Strong" if res.eps_beat_rate > 0.7 else "Good" if res.eps_beat_rate > 0.5 else "Mixed"
            if res.eps_trend == "Declining": res.rating = "Weak"
    except: pass
    return res
