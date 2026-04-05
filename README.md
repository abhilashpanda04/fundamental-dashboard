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

```bash
# Interactive mode — prompts for a ticker
finscope

# Jump straight to a ticker
finscope AAPL
finscope RELIANCE.NS
```

Once running, a numbered menu lets you drill into any data category.

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
| `tests/smoke/` | 44 | ❌ | Imports, wiring, object construction |
| `tests/unit/` | 153 | ❌ | All logic paths, fully mocked |
| `tests/integration/` | 27 | ✅ | Real Yahoo / SEC EDGAR / MFAPI calls |

---

## Architecture

```
src/finscope/
├── exceptions.py          # Typed exception hierarchy
├── config.py              # Singleton Config (env-var aware)
├── models.py              # Typed dataclasses (KeyRatios, ComparisonData, …)
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
└── cli.py                 # Command Pattern — each menu item is a Command class
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
