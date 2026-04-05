"""Typed output models for fund risk and analysis."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class FundVolatility:
    daily_vol: Optional[float] = None
    annual_vol: Optional[float] = None
    vol_30d: Optional[float] = None
    vol_90d: Optional[float] = None
    skewness: Optional[float] = None
    kurtosis: Optional[float] = None
    interpretation: str = "N/A"

@dataclass
class FundDownside:
    var_95: Optional[float] = None
    var_99: Optional[float] = None
    cvar_95: Optional[float] = None
    max_drawdown: Optional[float] = None
    max_drawdown_duration: Optional[int] = None
    drawdown_start: Optional[str] = None
    drawdown_end: Optional[str] = None
    current_drawdown: Optional[float] = None

@dataclass
class FundRiskAdjusted:
    annual_return: Optional[float] = None
    sharpe_ratio: Optional[float] = None
    sortino_ratio: Optional[float] = None
    calmar_ratio: Optional[float] = None
    interpretation: str = "N/A"

@dataclass
class FundRisk:
    name: str
    symbol: str = ""
    period: str = "1y"
    fund_type: str = "Global"
    volatility: FundVolatility = field(default_factory=FundVolatility)
    downside: FundDownside = field(default_factory=FundDownside)
    risk_adjusted: FundRiskAdjusted = field(default_factory=FundRiskAdjusted)
    beta: Optional[float] = None
    correlation_vs_market: Optional[float] = None
    r_squared: Optional[float] = None
    risk_score: Optional[float] = None
    risk_level: str = "N/A"
    risk_factors: list[str] = field(default_factory=list)
    risk_positives: list[str] = field(default_factory=list)

@dataclass
class FundAnalysis:
    name: str
    symbol: str = ""
    fund_type: str = "Global"
    category: str = "N/A"
    fund_house: str = "N/A"
    expense_ratio: Optional[float] = None
    expense_rating: str = "N/A"
    aum: Optional[float] = None
    aum_rating: str = "N/A"
    rolling_returns: dict[str, Optional[float]] = field(default_factory=dict)
    consistency_score: Optional[float] = None
    overall_rating: str = "N/A"
    highlights: list[str] = field(default_factory=list)
    concerns: list[str] = field(default_factory=list)
