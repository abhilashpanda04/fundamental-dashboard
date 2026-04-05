"""Valuation engine — runs all models and produces a composite verdict.

All calculations are pure functions operating on data from
``finscope.Stock``.  No network calls happen here — all data must
be passed in or fetched by the caller beforehand.
"""

from __future__ import annotations

import logging
import math
from typing import Optional

import pandas as pd

from finscope.valuation.models import (
    AltmanResult,
    DCFResult,
    GrahamResult,
    PEGResult,
    PiotroskiResult,
    RelativeResult,
    StockValuation,
)

logger = logging.getLogger(__name__)

__all__ = ["valuate"]


# ── Helper ────────────────────────────────────────────────────────────────────

def _safe_get(d: dict, *keys: str) -> Optional[float]:
    """Try multiple dict keys, return the first non-None float."""
    for k in keys:
        val = d.get(k)
        if val is not None:
            try:
                return float(val)
            except (TypeError, ValueError):
                continue
    return None


def _safe_div(a: Optional[float], b: Optional[float]) -> Optional[float]:
    """Safe division, returns None on any failure."""
    if a is None or b is None or b == 0:
        return None
    return a / b


def _pct_diff(current: Optional[float], target: Optional[float]) -> Optional[float]:
    """Percentage difference: how far current is from target."""
    if current is None or target is None or current == 0:
        return None
    return ((target - current) / current) * 100


def _signal_from_margin(margin: Optional[float], threshold: float = 15.0) -> str:
    """Convert margin of safety to a signal string."""
    if margin is None:
        return "N/A"
    if margin > threshold:
        return "Undervalued"
    if margin < -threshold:
        return "Overvalued"
    return "Fairly Valued"


# ── Individual Models ─────────────────────────────────────────────────────────


def _graham_number(info: dict) -> GrahamResult:
    """Benjamin Graham's intrinsic value: sqrt(22.5 × EPS × BVPS)."""
    eps = _safe_get(info, "trailingEps")
    bvps = _safe_get(info, "bookValue")
    price = _safe_get(info, "currentPrice", "regularMarketPrice")

    result = GrahamResult(eps=eps, book_value_per_share=bvps, current_price=price)

    if eps is not None and bvps is not None and eps > 0 and bvps > 0:
        result.intrinsic = math.sqrt(22.5 * eps * bvps)
        result.margin_of_safety_pct = _pct_diff(price, result.intrinsic)
        result.signal = _signal_from_margin(result.margin_of_safety_pct)

    return result


def _dcf_valuation(info: dict, financials_df: pd.DataFrame | None) -> DCFResult:
    """Simplified DCF using free cash flow and estimated growth."""
    fcf = _safe_get(info, "freeCashflow")
    beta = _safe_get(info, "beta") or 1.0
    price = _safe_get(info, "currentPrice", "regularMarketPrice")
    shares = _safe_get(info, "sharesOutstanding")
    revenue_growth = _safe_get(info, "revenueGrowth")
    earnings_growth = _safe_get(info, "earningsGrowth")

    # Estimate growth rate from available data
    growth = None
    if revenue_growth is not None and earnings_growth is not None:
        growth = (revenue_growth + earnings_growth) / 2
    elif revenue_growth is not None:
        growth = revenue_growth
    elif earnings_growth is not None:
        growth = earnings_growth

    # If we still don't have growth, try to compute from historical financials
    if growth is None and financials_df is not None and not financials_df.empty:
        try:
            revenue_row = None
            for idx in financials_df.index:
                if "revenue" in str(idx).lower() and "cost" not in str(idx).lower():
                    revenue_row = idx
                    break
            if revenue_row is not None:
                rev_values = financials_df.loc[revenue_row].dropna()
                if len(rev_values) >= 2:
                    latest = float(rev_values.iloc[0])
                    oldest = float(rev_values.iloc[-1])
                    years = len(rev_values) - 1
                    if oldest > 0 and years > 0:
                        growth = (latest / oldest) ** (1 / years) - 1
        except Exception:
            pass

    result = DCFResult(
        free_cash_flow=fcf,
        growth_rate=growth,
        shares_outstanding=shares,
        current_price=price,
    )

    if fcf is None or growth is None or shares is None or fcf <= 0:
        return result

    # Cap growth rate at reasonable bounds
    growth = max(min(growth, 0.30), -0.10)  # -10% to +30%

    # Discount rate: CAPM approximation
    risk_free = 0.04  # ~4% (10Y treasury proxy)
    market_premium = 0.06  # ~6% equity risk premium
    discount_rate = risk_free + beta * market_premium
    discount_rate = max(discount_rate, 0.06)  # floor at 6%
    result.discount_rate = discount_rate

    terminal_growth = result.terminal_growth
    years = result.projection_years

    # Project FCF and discount
    total_pv = 0.0
    projected_fcf = fcf
    for year in range(1, years + 1):
        projected_fcf *= (1 + growth)
        pv = projected_fcf / ((1 + discount_rate) ** year)
        total_pv += pv

    # Terminal value (Gordon Growth Model)
    terminal_fcf = projected_fcf * (1 + terminal_growth)
    terminal_value = terminal_fcf / (discount_rate - terminal_growth)
    terminal_pv = terminal_value / ((1 + discount_rate) ** years)
    total_pv += terminal_pv

    result.intrinsic = total_pv
    result.intrinsic_per_share = total_pv / shares
    result.margin_of_safety_pct = _pct_diff(price, result.intrinsic_per_share)
    result.signal = _signal_from_margin(result.margin_of_safety_pct)

    return result


def _peg_fair_value(info: dict) -> PEGResult:
    """Peter Lynch PEG-based fair price: Fair P/E = Growth Rate."""
    peg = _safe_get(info, "pegRatio")
    pe = _safe_get(info, "trailingPE")
    eps = _safe_get(info, "trailingEps")
    price = _safe_get(info, "currentPrice", "regularMarketPrice")
    growth = _safe_get(info, "earningsGrowth")

    # earningsGrowth is a decimal (e.g. 0.15 = 15%)
    growth_pct = growth * 100 if growth is not None else None

    result = PEGResult(
        peg_ratio=peg,
        trailing_pe=pe,
        earnings_growth_rate=growth_pct,
        eps=eps,
        current_price=price,
    )

    if eps is not None and growth_pct is not None and eps > 0 and growth_pct > 0:
        result.fair_price = growth_pct * eps  # Fair P/E = growth rate
        result.margin_of_safety_pct = _pct_diff(price, result.fair_price)
        result.signal = _signal_from_margin(result.margin_of_safety_pct)
    elif peg is not None:
        if peg < 0.8:
            result.signal = "Undervalued"
        elif peg > 1.5:
            result.signal = "Overvalued"
        else:
            result.signal = "Fairly Valued"

    return result


def _relative_valuation(info: dict) -> RelativeResult:
    """Compare current multiples vs historical price averages."""
    price = _safe_get(info, "currentPrice", "regularMarketPrice")
    avg_50 = _safe_get(info, "fiftyDayAverage")
    avg_200 = _safe_get(info, "twoHundredDayAverage")
    high_52 = _safe_get(info, "fiftyTwoWeekHigh")

    result = RelativeResult(
        pe_current=_safe_get(info, "trailingPE"),
        pe_5y_avg=_safe_get(info, "fiveYearAvgDividendYield"),  # proxy
        pb_current=_safe_get(info, "priceToBook"),
        ps_current=_safe_get(info, "priceToSalesTrailing12Months"),
        ev_ebitda_current=_safe_get(info, "enterpriseToEbitda"),
        dividend_yield=_safe_get(info, "dividendYield"),
        price_vs_50d=_pct_diff(avg_50, price) if avg_50 and price else None,
        price_vs_200d=_pct_diff(avg_200, price) if avg_200 and price else None,
        price_vs_52w_high=_pct_diff(high_52, price) if high_52 and price else None,
    )

    # Signal based on price vs moving averages
    signals = []
    if result.price_vs_200d is not None:
        if result.price_vs_200d < -10:
            signals.append("bearish")
        elif result.price_vs_200d > 10:
            signals.append("bullish")
        else:
            signals.append("neutral")

    pe = result.pe_current
    if pe is not None:
        if pe < 12:
            signals.append("bullish")
        elif pe > 35:
            signals.append("bearish")
        else:
            signals.append("neutral")

    if signals:
        bullish = signals.count("bullish")
        bearish = signals.count("bearish")
        if bullish > bearish:
            result.signal = "Undervalued"
        elif bearish > bullish:
            result.signal = "Overvalued"
        else:
            result.signal = "Fairly Valued"

    return result


def _piotroski_score(info: dict, financials: pd.DataFrame | None,
                     balance: pd.DataFrame | None) -> PiotroskiResult:
    """Piotroski F-Score: 9-criteria financial strength test."""
    details: dict[str, bool] = {}
    score = 0

    # ── Profitability (4 points) ──────────────────────────────────────────
    roa = _safe_get(info, "returnOnAssets")
    if roa is not None and roa > 0:
        details["Positive ROA"] = True
        score += 1
    else:
        details["Positive ROA"] = False

    ocf = _safe_get(info, "operatingCashflow")
    if ocf is not None and ocf > 0:
        details["Positive Operating CF"] = True
        score += 1
    else:
        details["Positive Operating CF"] = False

    # ROA improving — we check if current ROA is positive (simplified)
    details["ROA Improving"] = roa is not None and roa > 0.05
    if details["ROA Improving"]:
        score += 1

    # Quality of earnings: OCF > Net Income
    net_income = _safe_get(info, "netIncomeToCommon")
    if ocf is not None and net_income is not None and ocf > net_income:
        details["OCF > Net Income"] = True
        score += 1
    else:
        details["OCF > Net Income"] = False

    # ── Leverage / Liquidity (3 points) ───────────────────────────────────
    debt_equity = _safe_get(info, "debtToEquity")
    if debt_equity is not None and debt_equity < 100:  # < 1.0 ratio (reported as %)
        details["Low Debt/Equity"] = True
        score += 1
    else:
        details["Low Debt/Equity"] = False

    current_ratio = _safe_get(info, "currentRatio")
    if current_ratio is not None and current_ratio > 1.0:
        details["Current Ratio > 1"] = True
        score += 1
    else:
        details["Current Ratio > 1"] = False

    # No share dilution — check if shares outstanding is stable
    shares = _safe_get(info, "sharesOutstanding")
    float_shares = _safe_get(info, "floatShares")
    if shares and float_shares and float_shares / shares > 0.85:
        details["No Dilution"] = True
        score += 1
    else:
        details["No Dilution"] = shares is not None  # assume no dilution if we can't tell

    # ── Efficiency (2 points) ─────────────────────────────────────────────
    gross_margin = _safe_get(info, "grossMargins")
    if gross_margin is not None and gross_margin > 0.3:
        details["Healthy Gross Margin"] = True
        score += 1
    else:
        details["Healthy Gross Margin"] = False

    # Asset turnover: Revenue / Total Assets
    revenue = _safe_get(info, "totalRevenue")
    total_assets = _safe_get(info, "totalAssets")
    if revenue and total_assets and total_assets > 0:
        turnover = revenue / total_assets
        details["Good Asset Turnover"] = turnover > 0.5
        if details["Good Asset Turnover"]:
            score += 1
    else:
        details["Good Asset Turnover"] = False

    result = PiotroskiResult(score=score, details=details)
    if score >= 7:
        result.signal = "Undervalued"  # Strong financials
    elif score <= 3:
        result.signal = "Overvalued"   # Weak financials
    else:
        result.signal = "Fairly Valued"

    return result


def _altman_z_score(info: dict) -> AltmanResult:
    """Altman Z-Score: Z = 1.2A + 1.4B + 3.3C + 0.6D + 1.0E."""
    total_assets = _safe_get(info, "totalAssets")
    if not total_assets or total_assets == 0:
        return AltmanResult()

    # A = Working Capital / Total Assets
    current_assets = _safe_get(info, "totalCurrentAssets")
    current_liabilities = _safe_get(info, "totalCurrentLiabilities")
    working_capital = None
    if current_assets is not None and current_liabilities is not None:
        working_capital = current_assets - current_liabilities
    a = _safe_div(working_capital, total_assets)

    # B = Retained Earnings / Total Assets
    retained_earnings = _safe_get(info, "retainedEarnings")
    b = _safe_div(retained_earnings, total_assets)

    # C = EBIT / Total Assets
    ebit = _safe_get(info, "ebitda")  # EBITDA as proxy for EBIT
    c = _safe_div(ebit, total_assets)

    # D = Market Cap / Total Liabilities
    market_cap = _safe_get(info, "marketCap")
    total_liabilities = _safe_get(info, "totalDebt")
    d = _safe_div(market_cap, total_liabilities)

    # E = Revenue / Total Assets
    revenue = _safe_get(info, "totalRevenue")
    e = _safe_div(revenue, total_assets)

    components = {"A (WC/TA)": a, "B (RE/TA)": b, "C (EBIT/TA)": c,
                  "D (MC/TL)": d, "E (Rev/TA)": e}

    # Calculate Z-Score if we have enough components
    values = [a, b, c, d, e]
    if any(v is None for v in values):
        # Try with available components
        available = [(w, v) for w, v in zip([1.2, 1.4, 3.3, 0.6, 1.0], values) if v is not None]
        if len(available) < 3:
            return AltmanResult(components=components)
        z = sum(w * v for w, v in available)
    else:
        z = 1.2 * a + 1.4 * b + 3.3 * c + 0.6 * d + 1.0 * e

    if z > 2.99:
        zone = "Safe"
        signal = "Undervalued"
    elif z > 1.81:
        zone = "Grey"
        signal = "Fairly Valued"
    else:
        zone = "Distress"
        signal = "Overvalued"

    return AltmanResult(z_score=z, components=components, zone=zone, signal=signal)


# ── Composite Engine ──────────────────────────────────────────────────────────


def valuate(symbol: str, stock=None) -> StockValuation:
    """Run all valuation models and produce a composite verdict.

    Args:
        symbol: Ticker symbol (e.g. ``"AAPL"``).
        stock:  Optional pre-loaded ``finscope.Stock`` (for testing).

    Returns:
        A :class:`StockValuation` with individual model results and
        a composite verdict.
    """
    if stock is None:
        import finscope
        stock = finscope.stock(symbol)

    info = stock.info
    price = _safe_get(info, "currentPrice", "regularMarketPrice")

    # Fetch financial statements (may be empty)
    try:
        financials = stock.financials
    except Exception:
        financials = None
    try:
        balance = stock.balance_sheet
    except Exception:
        balance = None

    # Run all models
    graham = _graham_number(info)
    dcf = _dcf_valuation(info, financials)
    peg = _peg_fair_value(info)
    relative = _relative_valuation(info)
    piotroski = _piotroski_score(info, financials, balance)
    altman = _altman_z_score(info)

    # Collect signals
    models = [graham, dcf, peg, relative, piotroski, altman]
    signals = [m.signal for m in models if m.signal != "N/A"]

    bullish = sum(1 for s in signals if s == "Undervalued")
    bearish = sum(1 for s in signals if s == "Overvalued")
    neutral = sum(1 for s in signals if s == "Fairly Valued")

    # Composite verdict
    if not signals:
        verdict = "N/A"
        confidence = "Low"
    elif bullish > bearish and bullish > neutral:
        verdict = "Undervalued"
        confidence = "High" if bullish >= 4 else "Medium"
    elif bearish > bullish and bearish > neutral:
        verdict = "Overvalued"
        confidence = "High" if bearish >= 4 else "Medium"
    else:
        verdict = "Fairly Valued"
        confidence = "Medium" if len(signals) >= 4 else "Low"

    # Average margin of safety across calculable models
    margins = [
        m.margin_of_safety_pct
        for m in [graham, dcf, peg]
        if hasattr(m, "margin_of_safety_pct") and m.margin_of_safety_pct is not None
    ]
    avg_margin = sum(margins) / len(margins) if margins else None

    return StockValuation(
        symbol=symbol.upper(),
        current_price=price,
        graham=graham,
        dcf=dcf,
        peg=peg,
        relative=relative,
        piotroski=piotroski,
        altman=altman,
        verdict=verdict,
        confidence=confidence,
        margin_of_safety=avg_margin,
        signals_bullish=bullish,
        signals_bearish=bearish,
        signals_neutral=neutral,
    )
