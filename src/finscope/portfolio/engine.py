from __future__ import annotations
import json
from pathlib import Path
from finscope.portfolio.models import Holding, PortfolioSummary

_DEFAULT_FILE = Path.home() / ".finscope" / "portfolio.json"

class Portfolio:
    def __init__(self, path=None):
        self._path = Path(path) if path else _DEFAULT_FILE
        self._holdings = {}
        self._load()

    def _load(self):
        if self._path.exists():
            try: self._holdings = json.loads(self._path.read_text()).get("holdings", {})
            except: self._holdings = {}

    def _save(self):
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps({"holdings": self._holdings}, indent=2))

    def add(self, symbol, shares, cost):
        sym = symbol.upper()
        if sym in self._holdings:
            h = self._holdings[sym]
            total = h["shares"] + shares
            h["avg_cost"] = ((h["shares"] * h["avg_cost"]) + (shares * cost)) / total
            h["shares"] = total
        else: self._holdings[sym] = {"shares": shares, "avg_cost": cost}
        self._save()

    def remove(self, symbol):
        if symbol.upper() in self._holdings:
            del self._holdings[symbol.upper()]
            self._save(); return True
        return False

    def clear(self): self._holdings = {}; self._save()
    @property
    def is_empty(self): return not self._holdings
    @property
    def symbols(self): return list(self._holdings.keys())

    def summary(self):
        import finscope
        res = PortfolioSummary()
        for sym, data in self._holdings.items():
            try:
                s = finscope.stock(sym)
                info = s.info
                price = info.get("currentPrice") or info.get("regularMarketPrice")
                h = Holding(sym, data["shares"], data["avg_cost"], price, info.get("shortName"), info.get("sector"))
                res.holdings.append(h)
                res.total_cost += h.cost_basis
                res.total_value += (h.market_value or 0)
            except: pass
        res.total_pnl = res.total_value - res.total_cost
        res.total_pnl_pct = (res.total_pnl / res.total_cost * 100) if res.total_cost else 0
        res.num_holdings = len(res.holdings)
        return res
