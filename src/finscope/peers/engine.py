from __future__ import annotations
import concurrent.futures
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class PeerMetric:
    symbol: str
    name: str = ""
    market_cap: Optional[float] = None
    pe: Optional[float] = None
    profit_margin: Optional[float] = None

@dataclass
class PeerComparison:
    target_symbol: str
    target_name: str = ""
    sector: str = "N/A"
    industry: str = "N/A"
    target_metrics: PeerMetric = field(default_factory=lambda: PeerMetric(""))
    peers: list[PeerMetric] = field(default_factory=list)
    peer_count: int = 0
    pe_rank: Optional[str] = None
    margin_rank: Optional[str] = None
    growth_rank: Optional[str] = None
    highlights: list[str] = field(default_factory=list)

def _fetch_peer_info(symbol: str) -> Optional[PeerMetric]:
    try:
        import finscope
        s = finscope.stock(symbol)
        i = s.info
        return PeerMetric(symbol.upper(), i.get("shortName"), i.get("marketCap"), i.get("trailingPE"), i.get("profitMargins"))
    except: return None

def discover_peers(symbol: str, max_peers: int = 8, stock=None) -> PeerComparison:
    import finscope
    if stock is None: stock = finscope.stock(symbol)
    info = stock.info
    res = PeerComparison(symbol.upper(), info.get("shortName"), info.get("sector"), info.get("industry"))
    res.target_metrics = PeerMetric(symbol.upper(), info.get("shortName"), info.get("marketCap"), info.get("trailingPE"), info.get("profitMargins"))
    return res
