"""Domain model dataclasses for the Fundamental Dashboard.

Replacing raw ``dict`` pass-throughs with typed dataclasses gives us:
- IDE auto-complete and static-type-checking
- Clear contracts between layers
- Trivially mockable objects in tests
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

__all__ = [
    "StockQuote",
    "PriceBar",
    "KeyRatios",
    "ComparisonData",
    "SecFiling",
    "IndiaFundMeta",
    "NavRecord",
    "FundReturn",
]


# ── Stock / Equity ────────────────────────────────────────────────────────────

@dataclass
class StockQuote:
    """Snapshot of a stock's market data."""

    symbol: str
    name: str
    price: Optional[float]
    change_pct: Optional[float]
    currency: str = "USD"
    exchange: str = "N/A"
    sector: str = "N/A"
    industry: str = "N/A"
    description: str = ""


@dataclass
class PriceBar:
    """A single OHLCV price bar."""

    date: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int


@dataclass
class KeyRatios:
    """Key financial ratios extracted from a company info dict.

    All values default to ``None`` when the data provider does not supply
    them, so callers must always guard with ``if ratio.pe_ratio is not None``.
    """

    pe_ratio: Optional[float] = None
    forward_pe: Optional[float] = None
    peg_ratio: Optional[float] = None
    price_to_book: Optional[float] = None
    price_to_sales: Optional[float] = None
    ev_to_ebitda: Optional[float] = None
    profit_margin: Optional[float] = None
    operating_margin: Optional[float] = None
    roe: Optional[float] = None
    roa: Optional[float] = None
    debt_to_equity: Optional[float] = None
    current_ratio: Optional[float] = None
    revenue: Optional[float] = None
    ebitda: Optional[float] = None
    free_cash_flow: Optional[float] = None
    market_cap: Optional[float] = None
    enterprise_value: Optional[float] = None
    dividend_yield: Optional[float] = None
    beta: Optional[float] = None
    week_52_high: Optional[float] = None
    week_52_low: Optional[float] = None
    day_50_avg: Optional[float] = None
    day_200_avg: Optional[float] = None

    # ── Factory ──────────────────────────────────────────────────────────────

    @classmethod
    def from_info(cls, info: dict) -> "KeyRatios":
        """Construct a ``KeyRatios`` from a raw yfinance info dict."""
        return cls(
            pe_ratio=info.get("trailingPE"),
            forward_pe=info.get("forwardPE"),
            peg_ratio=info.get("pegRatio"),
            price_to_book=info.get("priceToBook"),
            price_to_sales=info.get("priceToSalesTrailing12Months"),
            ev_to_ebitda=info.get("enterpriseToEbitda"),
            profit_margin=info.get("profitMargins"),
            operating_margin=info.get("operatingMargins"),
            roe=info.get("returnOnEquity"),
            roa=info.get("returnOnAssets"),
            debt_to_equity=info.get("debtToEquity"),
            current_ratio=info.get("currentRatio"),
            revenue=info.get("totalRevenue"),
            ebitda=info.get("ebitda"),
            free_cash_flow=info.get("freeCashflow"),
            market_cap=info.get("marketCap"),
            enterprise_value=info.get("enterpriseValue"),
            dividend_yield=info.get("dividendYield"),
            beta=info.get("beta"),
            week_52_high=info.get("fiftyTwoWeekHigh"),
            week_52_low=info.get("fiftyTwoWeekLow"),
            day_50_avg=info.get("fiftyDayAverage"),
            day_200_avg=info.get("twoHundredDayAverage"),
        )

    def to_display_dict(self) -> dict[str, Optional[float]]:
        """Return an ordered dict with human-readable labels for UI rendering."""
        return {
            "P/E Ratio": self.pe_ratio,
            "Forward P/E": self.forward_pe,
            "PEG Ratio": self.peg_ratio,
            "Price/Book": self.price_to_book,
            "Price/Sales": self.price_to_sales,
            "EV/EBITDA": self.ev_to_ebitda,
            "Profit Margin": self.profit_margin,
            "Operating Margin": self.operating_margin,
            "Return on Equity": self.roe,
            "Return on Assets": self.roa,
            "Debt/Equity": self.debt_to_equity,
            "Current Ratio": self.current_ratio,
            "Revenue": self.revenue,
            "EBITDA": self.ebitda,
            "Free Cash Flow": self.free_cash_flow,
            "Market Cap": self.market_cap,
            "Enterprise Value": self.enterprise_value,
            "Dividend Yield": self.dividend_yield,
            "Beta": self.beta,
            "52W High": self.week_52_high,
            "52W Low": self.week_52_low,
            "50D Avg": self.day_50_avg,
            "200D Avg": self.day_200_avg,
        }


@dataclass
class ComparisonData:
    """Data for a single ticker in a side-by-side comparison view."""

    symbol: str
    name: str
    price: Optional[float]
    change_pct: Optional[float]
    market_cap: Optional[float]
    pe_ratio: Optional[float]
    forward_pe: Optional[float]
    peg: Optional[float]
    pb: Optional[float]
    ps: Optional[float]
    profit_margin: Optional[float]
    roe: Optional[float]
    debt_equity: Optional[float]
    dividend_yield: Optional[float]
    beta: Optional[float]
    revenue: Optional[float]
    ebitda: Optional[float]
    sparkline: list[float] = field(default_factory=list)

    @classmethod
    def from_info(cls, symbol: str, info: dict, sparkline: list[float] | None = None) -> "ComparisonData":
        """Construct from a raw yfinance info dict."""
        return cls(
            symbol=symbol.upper(),
            name=info.get("shortName", "N/A"),
            price=info.get("currentPrice") or info.get("regularMarketPrice"),
            change_pct=info.get("regularMarketChangePercent"),
            market_cap=info.get("marketCap"),
            pe_ratio=info.get("trailingPE"),
            forward_pe=info.get("forwardPE"),
            peg=info.get("pegRatio"),
            pb=info.get("priceToBook"),
            ps=info.get("priceToSalesTrailing12Months"),
            profit_margin=info.get("profitMargins"),
            roe=info.get("returnOnEquity"),
            debt_equity=info.get("debtToEquity"),
            dividend_yield=info.get("dividendYield"),
            beta=info.get("beta"),
            revenue=info.get("totalRevenue"),
            ebitda=info.get("ebitda"),
            sparkline=sparkline or [],
        )


# ── SEC EDGAR ─────────────────────────────────────────────────────────────────

@dataclass
class SecFiling:
    """A single SEC filing entry."""

    form: str
    date: str
    accession: str
    document: str
    description: str
    url: str


# ── Mutual Funds ──────────────────────────────────────────────────────────────

@dataclass
class IndiaFundMeta:
    """Metadata for an Indian SEBI-registered mutual fund (from MFAPI)."""

    scheme_code: str
    scheme_name: str
    fund_house: str
    scheme_category: str
    scheme_type: str
    isin: Optional[str] = None


@dataclass
class NavRecord:
    """A single NAV (Net Asset Value) data point."""

    date: datetime
    nav: float


@dataclass
class FundReturn:
    """Point-to-point return for one time period."""

    period: str
    return_pct: Optional[float]
    start_nav: Optional[float]
    current_nav: Optional[float]
    start_date: str
