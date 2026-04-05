"""Risk engine — pure financial math, no AI required."""
from __future__ import annotations
import logging
import math
from typing import Optional
import numpy as np
import pandas as pd
from finscope.risk.models import (
    DownsideRisk, FundamentalRisk, MarketRisk, RiskAdjustedMetrics, StockRisk, VolatilityMetrics
)
logger = logging.getLogger(__name__)
__all__ = ["compute_risk"]
RISK_FREE_RATE = 0.04
TRADING_DAYS = 252

def _safe(x) -> Optional[float]:
    try:
        f = float(x)
        return None if (math.isnan(f) or math.isinf(f)) else f
    except: return None

def _daily_returns(prices: pd.DataFrame) -> pd.Series:
    return prices["Close"].pct_change().dropna()

def _compute_volatility(returns: pd.Series) -> VolatilityMetrics:
    if returns.empty: return VolatilityMetrics()
    daily = _safe(returns.std())
    annual = _safe(daily * math.sqrt(252)) if daily else None
    interp = "Low" if (annual or 0) < 0.15 else "Moderate" if (annual or 0) < 0.25 else "High" if (annual or 0) < 0.40 else "Very High"
    return VolatilityMetrics(daily_vol=daily, annual_vol=annual, interpretation=interp,
                             vol_30d=_safe(returns.tail(30).std()*math.sqrt(252)),
                             vol_90d=_safe(returns.tail(90).std()*math.sqrt(252)),
                             skewness=_safe(returns.skew()), kurtosis=_safe(returns.kurtosis()))

def _compute_downside(returns, prices, info):
    res = DownsideRisk()
    if returns.empty: return res
    res.var_95, res.var_99 = _safe(np.percentile(returns, 5)), _safe(np.percentile(returns, 1))
    res.cvar_95 = _safe(returns[returns <= (res.var_95 or 0)].mean())
    close = prices["Close"]
    drawdown = (close - close.cummax()) / close.cummax()
    res.max_drawdown = _safe(drawdown.min())
    price = _safe(info.get("currentPrice") or info.get("regularMarketPrice"))
    high = _safe(info.get("fiftyTwoWeekHigh"))
    if price and high: res.current_drawdown = (price - high) / high
    return res

def _compute_risk_adjusted(returns, downside, vol):
    res = RiskAdjustedMetrics()
    if returns.empty: return res
    ann_return = _safe((1 + ((1 + returns).prod() - 1)) ** (252 / len(returns)) - 1)
    res.annual_return = ann_return
    if vol.daily_vol:
        res.sharpe_ratio = _safe((returns.mean() - (1.04**(1/252)-1)) / vol.daily_vol * math.sqrt(252))
        neg = returns[returns < 0]
        if not neg.empty:
            res.sortino_ratio = _safe((ann_return - 0.04) / (neg.std() * math.sqrt(252)))
    res.interpretation = "Good" if (res.sharpe_ratio or 0) > 1 else "Poor"
    return res

def _compute_market_risk(returns, info, m_returns):
    res = MarketRisk(beta=_safe(info.get("beta")))
    if m_returns is not None:
        aligned = pd.concat([returns, m_returns], axis=1).dropna()
        if len(aligned) >= 30:
            res.correlation = _safe(aligned.corr().iloc[0,1])
            res.r_squared = _safe(res.correlation**2) if res.correlation is not None else None
            res.beta_calculated = _safe(aligned.cov().iloc[0,1] / aligned.iloc[:,1].var())
    beta = res.beta or res.beta_calculated
    res.interpretation = "Aggressive" if (beta or 0) > 1.2 else "Defensive" if (beta or 0) < 0.8 else "Moderate"
    return res

def _compute_fundamental_risk(info):
    from finscope.valuation.engine import _altman_z_score
    az = _altman_z_score(info)
    res = FundamentalRisk(debt_to_equity=_safe(info.get("debtToEquity")), current_ratio=_safe(info.get("currentRatio")),
                          altman_z=az.z_score, altman_zone=az.zone)
    ebit, ie = _safe(info.get("ebit")), _safe(info.get("interestExpense"))
    if ebit and ie: res.interest_coverage = abs(ebit)/abs(ie)
    ocf, ni = _safe(info.get("operatingCashflow")), _safe(info.get("netIncomeToCommon"))
    res.earnings_quality = "Good" if (ocf and ni and ocf > ni) else "Weak"
    res.interpretation = "High Risk" if (res.debt_to_equity or 0) > 200 or az.zone == "Distress" else "Low Risk" if az.zone == "Safe" else "Moderate Risk"
    return res

def _composite_score(vol, downside, risk_adj, market, fund):
    score = 0.0
    factors, positives = [], []
    if (vol.annual_vol or 0) > 0.4: score += 40; factors.append("High Vol")
    else: positives.append("Low Vol")
    if (downside.max_drawdown or 0) < -0.3: score += 40; factors.append("Large Drawdown")
    else: positives.append("Low Drawdown")
    level = "Low" if score < 25 else "High" if score > 60 else "Moderate"
    return score, level, factors, positives

def compute_risk(symbol: str, period: str = "1y", stock=None) -> StockRisk:
    import finscope
    if stock is None: stock = finscope.stock(symbol)
    info, prices = stock.info, stock.price_history(period)
    if prices is None or prices.empty: return StockRisk(symbol.upper())
    returns = _daily_returns(prices)
    m_rets = None
    try:
        spy = finscope.stock("SPY").price_history(period)
        spy_rets = _daily_returns(spy)
        idx1, idx2 = returns.index.tz_localize(None) if returns.index.tzinfo else returns.index, spy_rets.index.tz_localize(None) if spy_rets.index.tzinfo else spy_rets.index
        returns.index, spy_rets.index = idx1, idx2
        m_rets = spy_rets
    except: pass
    vol, down = _compute_volatility(returns), _compute_downside(returns, prices, info)
    ra, mkt = _compute_risk_adjusted(returns, down, vol), _compute_market_risk(returns, info, m_rets)
    fnd = _compute_fundamental_risk(info)
    score, level, fact, pos = _composite_score(vol, down, ra, mkt, fnd)
    return StockRisk(symbol.upper(), period, info.get("currentPrice"), vol, down, ra, mkt, fnd, score, level, fact, pos)
