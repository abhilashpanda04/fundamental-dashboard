"""Valuation engine — pure financial logic, no AI required.

Implements classic valuation models to assess whether a stock is
undervalued, fairly valued, or overvalued. Every calculation is
transparent and based on publicly available financial data.

Usage::

    import finscope

    aapl = finscope.stock("AAPL")
    v = aapl.valuate()

    v.verdict              # "Fairly Valued"
    v.margin_of_safety     # -5.2%
    v.graham.intrinsic     # 112.45
    v.dcf.intrinsic        # 165.30
    v.piotroski.score      # 7
    v.altman.z_score       # 3.2
"""

from finscope.valuation.models import (
    StockValuation,
    GrahamResult,
    DCFResult,
    PEGResult,
    RelativeResult,
    PiotroskiResult,
    AltmanResult,
)
from finscope.valuation.engine import valuate

__all__ = [
    "valuate",
    "StockValuation",
    "GrahamResult",
    "DCFResult",
    "PEGResult",
    "RelativeResult",
    "PiotroskiResult",
    "AltmanResult",
]
