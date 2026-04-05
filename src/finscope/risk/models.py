"""Typed output models for the risk engine."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class VolatilityMetrics:
    daily_vol: Optional[float] = None
    annual_vol: Optional[float] = None
    vol_30d: Optional[float] = None
    vol_90d: Optional[float] = None
    skewness: Optional[float] = None
    kurtosis: Optional[float] = None
    interpretation: str = "N/A"

@dataclass
class DownsideRisk:
    var_95: Optional[float] = None
    var_99: Optional[float] = None
    cvar_95: Optional[float] = None
    max_drawdown: Optional[float] = None
    max_drawdown_duration: Optional[int] = None
    drawdown_start: Optional[str] = None
    drawdown_end: Optional[str] = None
    current_drawdown: Optional[float] = None

@dataclass
class RiskAdjustedMetrics:
    risk_free_rate: float = 0.04
    annual_return: Optional[float] = None
    sharpe_ratio: Optional[float] = None
    sortino_ratio: Optional[float] = None
    calmar_ratio: Optional[float] = None
    interpretation: str = "N/A"

@dataclass
class MarketRisk:
    beta: Optional[float] = None
    beta_calculated: Optional[float] = None
    r_squared: Optional[float] = None
    correlation: Optional[float] = None
    interpretation: str = "N/A"

@dataclass
class FundamentalRisk:
    debt_to_equity: Optional[float] = None
    current_ratio: Optional[float] = None
    interest_coverage: Optional[float] = None
    altman_z: Optional[float] = None
    altman_zone: str = "N/A"
    earnings_quality: str = "N/A"
    interpretation: str = "N/A"

@dataclass
class StockRisk:
    symbol: str
    period: str = "1y"
    current_price: Optional[float] = None
    volatility: VolatilityMetrics = field(default_factory=VolatilityMetrics)
    downside: DownsideRisk = field(default_factory=DownsideRisk)
    risk_adjusted: RiskAdjustedMetrics = field(default_factory=RiskAdjustedMetrics)
    market: MarketRisk = field(default_factory=MarketRisk)
    fundamental: FundamentalRisk = field(default_factory=FundamentalRisk)
    risk_score: Optional[float] = None
    risk_level: str = "N/A"
    risk_factors: list[str] = field(default_factory=list)
    risk_positives: list[str] = field(default_factory=list)
