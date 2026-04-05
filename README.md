# 🔭 finscope

> A terminal-based financial research tool powered by **Yahoo Finance**, **SEC EDGAR**, and **Rich**.

Scope deeply into any stock, ETF, or mutual fund — all from your terminal, with no API keys required.

---

## Features

| Category | What you get |
|---|---|
| **Stock Overview** | Name, sector, price, live change %, 3-month sparkline |
| **Key Ratios** | P/E, Forward P/E, PEG, P/B, P/S, EV/EBITDA, margins, ROE, debt/equity, beta, 52-week range |
| **Price History** | OHLCV table + ASCII sparkline for any period (1d → max) |
| **Financial Statements** | Income statement, balance sheet, cash flow (Yahoo Finance) |
| **SEC EDGAR** | XBRL financials (7 categories, 6 fiscal years), recent filings browser, insider transactions |
| **Analyst Recs** | Buy / Hold / Sell bar chart |
| **Holders** | Ownership breakdown + top institutional holders |
| **Comparison** | Side-by-side metrics for up to 10 tickers with sparklines |
| **Watchlist** | Compact multi-ticker table |
| **Mutual Funds** | 37,500+ Indian funds (MFAPI.in) + US/global/Asia/European ETFs via Yahoo Finance |
| **HTML Export** | One-click report export with ratios and price history |

---

## Installation

```bash
git clone https://github.com/abhilashpanda04/fundamental-dashboard.git
cd fundamental-dashboard
uv sync              # or: pip install -e .
```

### Dev / testing dependencies

```bash
uv sync --dev        # or: pip install -e ".[dev]"
```

---

## Usage

### Direct commands (default)

```bash
finscope AAPL                       # Quick overview
finscope AAPL ratios                # Key financial ratios
finscope AAPL price 1y              # Price history (1 year)
finscope AAPL financials            # Income statement
finscope AAPL balance-sheet         # Balance sheet
finscope AAPL cashflow              # Cash flow statement
finscope AAPL news                  # Recent news
finscope AAPL analysts              # Analyst recommendations
finscope AAPL holders               # Major holders
finscope AAPL sec-financials        # SEC EDGAR XBRL financials
finscope AAPL sec-filings           # Recent SEC filings
finscope AAPL insiders              # Insider transactions
finscope compare AAPL MSFT GOOGL    # Side-by-side comparison
finscope watchlist AAPL TSLA NVDA   # Compact watchlist
finscope export AAPL                # HTML report → aapl_report.html
finscope export AAPL -o report.html # Custom output path
finscope funds                      # Mutual funds explorer
```

### Interactive mode (opt-in)

```bash
finscope AAPL -i          # Menu loop for AAPL
finscope -i               # Prompts for ticker, then menu
```

### As a Python library

```python
import finscope

# Single stock — lazy, cached, typed
aapl = finscope.stock("AAPL")
aapl.ratios.pe_ratio           # 28.5
aapl.ratios.market_cap         # 2_700_000_000_000
aapl.price_history("1y")       # pandas DataFrame
aapl.sparkline                 # [100.0, 105.3, …]
aapl.news                      # list of article dicts
aapl.financials                # income statement DataFrame
aapl.sec_financials            # XBRL data from SEC EDGAR
aapl.insider_transactions      # Form 4 filings
aapl.export_html()             # → aapl_report.html

# Multi-stock comparison
aapl.compare_with("MSFT", "GOOGL")    # list[ComparisonData]
finscope.compare("AAPL", "MSFT")      # standalone

# Global ETF / mutual fund
vwrl = finscope.fund("VWRL.L")
vwrl.info / vwrl.returns / vwrl.sparkline
```

---

## Running Tests

```bash
# Fast unit + smoke tests (no network, ~0.6 s)
pytest

# Include live API integration tests
pytest -m integration -v

# With coverage report
pytest --cov=finscope --cov-report=term-missing
```

### Test breakdown

| Suite | Count | Network? | Purpose |
|---|---|---|---|
| `tests/smoke/` | 54 | ❌ | Imports, wiring, object construction, dispatch |
| `tests/unit/` | 244 | ❌ | All logic paths, fully mocked |
| `tests/integration/` | 27 | ✅ | Real Yahoo / SEC EDGAR / MFAPI calls |

---

## Architecture

```
src/finscope/
├── exceptions.py          # Typed exception hierarchy
├── config.py              # Singleton Config (env-var aware)
├── models.py              # Typed dataclasses (KeyRatios, ComparisonData, …)
│
├── stock.py               # Stock + Fund façade classes (library entry points)
│
├── providers/             # Strategy Pattern — one class per data source
│   ├── base.py            #   Abstract interfaces
│   ├── yahoo_provider.py  #   Yahoo Finance via yfinance
│   ├── sec_edgar_provider.py # SEC EDGAR XBRL + filings
│   └── mfapi_provider.py  #   MFAPI.in (India) + Yahoo (global ETFs)
│
├── services/              # Facade Pattern — orchestrate providers
│   ├── stock_service.py   #   All stock operations
│   └── fund_service.py    #   All fund operations
│
├── ui/                    # Presentation layer
│   ├── formatters.py      #   Pure formatting functions
│   ├── builders.py        #   Builder Pattern for Rich tables
│   └── renderers.py       #   All render functions
│
└── cli.py                 # Direct subcommands + opt-in interactive menu (-i)
```

### Design patterns used

| Pattern | Where | Why |
|---|---|---|
| **Strategy** | `providers/` | Swap data sources without touching callers |
| **Facade** | `services/` | Single clean API over complex provider coordination |
| **Builder** | `ui/builders.py` | Eliminate repetitive Rich table boilerplate |
| **Command** | `cli.py` | Each menu option is independently testable; zero if/elif |
| **Singleton** | `config.py` | One source of truth for all settings |

---

## Data Sources

| Source | Data | API Key? |
|---|---|---|
| [Yahoo Finance](https://finance.yahoo.com) | Prices, ratios, financials, news, ETFs | ❌ Free |
| [SEC EDGAR](https://www.sec.gov/edgar) | XBRL financials, filings, insider trades | ❌ Free |
| [MFAPI.in](https://www.mfapi.in) | 37,500+ Indian mutual fund NAV histories | ❌ Free |

SEC EDGAR asks for a contact e-mail in the User-Agent header per their fair-access policy.  
Set `SEC_EDGAR_EMAIL=your@email.com` in your environment to customise it.

---

## Environment Variables

| Variable | Default | Purpose |
|---|---|---|
| `SEC_EDGAR_EMAIL` | `finscope-user@example.com` | SEC EDGAR User-Agent contact e-mail |
