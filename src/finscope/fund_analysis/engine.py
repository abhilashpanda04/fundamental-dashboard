"""Fund risk and analysis engine."""
from __future__ import annotations
import math
import pandas as pd
from finscope.fund_analysis.models import FundAnalysis, FundDownside, FundRisk, FundRiskAdjusted, FundVolatility
from finscope.risk.engine import _compute_downside, _compute_risk_adjusted, _compute_volatility, _daily_returns, _safe

def _nav_list_to_df(nav_data):
    rows = []
    for e in reversed(nav_data):
        if "nav" not in e or "date" not in e: continue
        try:
            rows.append({"date": pd.to_datetime(e["date"], dayfirst=True), "Close": float(e["nav"])})
        except: continue
    return pd.DataFrame(rows).set_index("date").sort_index() if rows else pd.DataFrame()

def _compute_fund_volatility(returns):
    v = _compute_volatility(returns)
    return FundVolatility(v.daily_vol, v.annual_vol, v.vol_30d, v.vol_90d, v.skewness, v.kurtosis, v.interpretation)

def _compute_fund_downside(returns, prices, info):
    d = _compute_downside(returns, prices, info)
    return FundDownside(d.var_95, d.var_99, d.cvar_95, d.max_drawdown, d.max_drawdown_duration, d.drawdown_start, d.drawdown_end, d.current_drawdown)

def _compute_fund_risk_adjusted(returns, downside, vol):
    from finscope.risk.models import DownsideRisk, VolatilityMetrics
    ra = _compute_risk_adjusted(returns, DownsideRisk(max_drawdown=downside.max_drawdown), VolatilityMetrics(daily_vol=vol.daily_vol, annual_vol=vol.annual_vol))
    return FundRiskAdjusted(ra.annual_return, ra.sharpe_ratio, ra.sortino_ratio, ra.calmar_ratio, ra.interpretation)

def _expense_rating(er, fund_type):
    if er is None: return "N/A"
    if fund_type == "India": return "Excellent" if er < 0.005 else "Good" if er < 0.01 else "Very High" if er > 0.02 else "Average"
    return "Excellent" if er < 0.001 else "Good" if er < 0.003 else "Very High" if er > 0.015 else "Average"

def _aum_rating(aum):
    if aum is None: return "N/A"
    return "Large" if aum > 10e9 else "Medium" if aum > 1e9 else "Small" if aum > 100e6 else "Micro"

def _rolling_returns(prices):
    if prices.empty: return {}
    close, res = prices["Close"], {}
    for l, d in {"1M":21, "3M":63, "6M":126, "1Y":252, "3Y":756, "5Y":1260}.items():
        if len(close) >= d: res[l] = _safe((close.iloc[-1] / close.iloc[-d])**(252/d) - 1)
        else: res[l] = None
    return res

def _consistency_score(prices):
    if len(prices) <= 252: return None
    c = prices["Close"]
    return sum(1 for i in range(252, len(c)) if c.iloc[i] > c.iloc[i-252]) / (len(c)-252)

def _overall_rating(rolling, expense_rating, sharpe, consistency):
    if (rolling.get("1Y") or 0) < 0: return "Weak", [], ["Negative Return"]
    return "Good", ["Consistent"], []

def analyze_global_fund(symbol, fund=None, period="1y"):
    import finscope
    if fund is None: fund = finscope.fund(symbol)
    info = fund.info or {}
    try: prices = fund._service.get_price_history(symbol, period=period)
    except: prices = None
    if prices is None or prices.empty: return FundRisk(symbol), FundAnalysis(symbol)
    vol, down = _compute_fund_volatility(_daily_returns(prices)), _compute_fund_downside(_daily_returns(prices), prices, info)
    ra = _compute_fund_risk_adjusted(_daily_returns(prices), down, vol)
    rolling, consistency = _rolling_returns(prices), _consistency_score(prices)
    er = info.get("annualReportExpenseRatio") or info.get("expenseRatio")
    analysis = FundAnalysis(info.get("longName", symbol), symbol, "Global", info.get("category"), info.get("fundFamily"), er, _expense_rating(er, "Global"), info.get("totalAssets"), _aum_rating(info.get("totalAssets")), rolling, consistency, "Strong" if (er or 1) < 0.001 else "Good")
    return FundRisk(info.get("longName", symbol), symbol, period, "Global", vol, down, ra, risk_score=50, risk_level="Moderate"), analysis

def analyze_india_fund(nav_data, meta):
    prices = _nav_list_to_df(nav_data)
    if prices.empty: return FundRisk(meta.get("scheme_name")), FundAnalysis(meta.get("scheme_name"))
    vol, down = _compute_fund_volatility(_daily_returns(prices)), _compute_fund_downside(_daily_returns(prices), prices, {})
    ra = _compute_fund_risk_adjusted(_daily_returns(prices), down, vol)
    rolling, consistency = _rolling_returns(prices), _consistency_score(prices)
    return FundRisk(meta.get("scheme_name"), "", "1y", "India", vol, down, ra, risk_score=50, risk_level="Moderate"), FundAnalysis(meta.get("scheme_name"), "", "India", meta.get("scheme_category"), meta.get("fund_house"), None, "N/A", None, "N/A", rolling, consistency, "Good")
