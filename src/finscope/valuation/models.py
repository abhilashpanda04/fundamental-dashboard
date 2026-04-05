"""Typed output models for the valuation engine.

Every model returns a structured result with the computed value,
an interpretation, and the inputs used — full transparency.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

__all__ = [
    "StockValuation",
    "GrahamResult",
    "DCFResult",
    "PEGResult",
    "RelativeResult",
    "PiotroskiResult",
    "AltmanResult",
]


@dataclass
class GrahamResult:
    """Benjamin Graham's intrinsic value calculation.

    Formula: ``intrinsic = sqrt(22.5 × EPS × Book Value Per Share)``

    A stock trading below its Graham Number has a margin of safety.
    """

    eps: Optional[float] = None
    book_value_per_share: Optional[float] = None
    intrinsic: Optional[float] = None
    current_price: Optional[float] = None
    margin_of_safety_pct: Optional[float] = None
    signal: str = "N/A"  # "Undervalued", "Overvalued", "Fairly Valued", "N/A"

    @property
    def calculable(self) -> bool:
        return self.intrinsic is not None


@dataclass
class DCFResult:
    """Simplified Discounted Cash Flow valuation.

    Projects free cash flow forward using historical growth rates,
    discounts at WACC (approximated from beta + risk-free rate),
    and adds a terminal value.
    """

    free_cash_flow: Optional[float] = None
    growth_rate: Optional[float] = None
    discount_rate: Optional[float] = None
    terminal_growth: float = 0.03  # 3% perpetual growth
    projection_years: int = 5
    intrinsic: Optional[float] = None
    intrinsic_per_share: Optional[float] = None
    current_price: Optional[float] = None
    margin_of_safety_pct: Optional[float] = None
    signal: str = "N/A"
    shares_outstanding: Optional[float] = None

    @property
    def calculable(self) -> bool:
        return self.intrinsic_per_share is not None


@dataclass
class PEGResult:
    """Peter Lynch PEG-based fair value.

    Fair P/E equals the earnings growth rate. A PEG < 1 suggests
    the stock is undervalued relative to its growth.

    ``fair_price = earnings_growth_rate × EPS``
    """

    peg_ratio: Optional[float] = None
    trailing_pe: Optional[float] = None
    earnings_growth_rate: Optional[float] = None
    eps: Optional[float] = None
    fair_price: Optional[float] = None
    current_price: Optional[float] = None
    margin_of_safety_pct: Optional[float] = None
    signal: str = "N/A"

    @property
    def calculable(self) -> bool:
        return self.fair_price is not None


@dataclass
class RelativeResult:
    """Relative valuation — current multiples vs historical averages.

    Compares current P/E, P/B, P/S, EV/EBITDA against the stock's
    own 50-day and 200-day averages, and against the sector if available.
    """

    pe_current: Optional[float] = None
    pe_5y_avg: Optional[float] = None
    pb_current: Optional[float] = None
    ps_current: Optional[float] = None
    ev_ebitda_current: Optional[float] = None
    dividend_yield: Optional[float] = None
    price_vs_50d: Optional[float] = None   # % above/below 50-day avg
    price_vs_200d: Optional[float] = None  # % above/below 200-day avg
    price_vs_52w_high: Optional[float] = None  # % below 52-week high
    signal: str = "N/A"

    @property
    def calculable(self) -> bool:
        return self.pe_current is not None


@dataclass
class PiotroskiResult:
    """Piotroski F-Score — 9-point financial strength test.

    Each criterion adds 1 point:
        Profitability (4):  ROA > 0, OCF > 0, ROA improving, OCF > Net Income
        Leverage (3):       Debt ratio decreasing, current ratio improving, no dilution
        Efficiency (2):     Gross margin improving, asset turnover improving

    Interpretation:
        8-9: Strong    5-7: Moderate    0-4: Weak
    """

    score: int = 0
    max_score: int = 9
    details: dict[str, bool] = field(default_factory=dict)
    signal: str = "N/A"

    @property
    def strength(self) -> str:
        if self.score >= 8:
            return "Strong"
        if self.score >= 5:
            return "Moderate"
        return "Weak"


@dataclass
class AltmanResult:
    """Altman Z-Score — bankruptcy risk indicator.

    Formula: ``Z = 1.2A + 1.4B + 3.3C + 0.6D + 1.0E``
        A = Working Capital / Total Assets
        B = Retained Earnings / Total Assets
        C = EBIT / Total Assets
        D = Market Cap / Total Liabilities
        E = Revenue / Total Assets

    Interpretation:
        Z > 2.99:  Safe zone
        1.81–2.99: Grey zone
        Z < 1.81:  Distress zone
    """

    z_score: Optional[float] = None
    components: dict[str, Optional[float]] = field(default_factory=dict)
    zone: str = "N/A"  # "Safe", "Grey", "Distress"
    signal: str = "N/A"

    @property
    def calculable(self) -> bool:
        return self.z_score is not None


@dataclass
class StockValuation:
    """Composite valuation result combining all models.

    The ``verdict`` and ``confidence`` fields synthesize signals from
    every individual model into one actionable assessment.
    """

    symbol: str
    current_price: Optional[float] = None

    # Individual model results
    graham: GrahamResult = field(default_factory=GrahamResult)
    dcf: DCFResult = field(default_factory=DCFResult)
    peg: PEGResult = field(default_factory=PEGResult)
    relative: RelativeResult = field(default_factory=RelativeResult)
    piotroski: PiotroskiResult = field(default_factory=PiotroskiResult)
    altman: AltmanResult = field(default_factory=AltmanResult)

    # Composite assessment
    verdict: str = "N/A"        # "Undervalued", "Fairly Valued", "Overvalued"
    confidence: str = "N/A"     # "High", "Medium", "Low"
    margin_of_safety: Optional[float] = None  # average margin across models
    signals_bullish: int = 0
    signals_bearish: int = 0
    signals_neutral: int = 0

    def __repr__(self) -> str:
        return (
            f"StockValuation('{self.symbol}' | "
            f"price={self.current_price} | "
            f"verdict={self.verdict} | "
            f"confidence={self.confidence} | "
            f"margin_of_safety={self.margin_of_safety:.1f}%)"
            if self.margin_of_safety is not None
            else f"StockValuation('{self.symbol}' | verdict={self.verdict})"
        )
