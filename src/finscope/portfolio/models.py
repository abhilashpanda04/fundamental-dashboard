from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class Holding:
    symbol: str
    shares: float
    avg_cost: float
    current_price: Optional[float] = None
    name: Optional[str] = None
    sector: Optional[str] = None

    @property
    def cost_basis(self) -> float: return self.shares * self.avg_cost
    @property
    def market_value(self) -> Optional[float]: return self.shares * self.current_price if self.current_price else None
    @property
    def pnl(self) -> Optional[float]: return self.market_value - self.cost_basis if self.market_value is not None else None
    @property
    def pnl_pct(self) -> Optional[float]: return (self.pnl / self.cost_basis * 100) if self.pnl is not None and self.cost_basis else None

@dataclass
class PortfolioSummary:
    holdings: list[Holding] = field(default_factory=list)
    total_cost: float = 0.0
    total_value: float = 0.0
    total_pnl: float = 0.0
    total_pnl_pct: float = 0.0
    daily_change: float = 0.0
    daily_change_pct: float = 0.0
    num_holdings: int = 0
    sectors: dict[str, float] = field(default_factory=dict)
    weighted_beta: Optional[float] = None
    weighted_pe: Optional[float] = None
