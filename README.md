```text
 _____ _       ____
|  ___(_)_ __ / ___|  ___ ___  _ __   ___
| |_  | | '_ \\___ \ / __/ _ \| '_ \ / _ \\
|  _| | | | | |___) | (_| (_) | |_) |  __/
|_|   |_|_| |_|____/ \___\___/| .__/ \___|
                               |_|        
```

# finscope

Terminal-based financial research for stocks, ETFs, and mutual funds.

[![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)](https://github.com/abhilashpanda04/finscope)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

`finscope` is a command-line research tool and Python library for market analysis. It combines price history, fundamentals, SEC filings, fund discovery, valuation models, risk analytics, and terminal-first rendering in a single workflow.

It is built for people who want fast, structured financial research without depending on spreadsheets or browser-heavy tooling.

## Highlights

- Stock, ETF, and mutual fund research from the terminal
- SEC EDGAR integration for official US filing data
- Valuation and risk engines built into the CLI
- Interactive dashboard mode with segmented menus
- Fund support for global ETFs and Indian mutual funds
- Python API with lazy-loaded objects and typed models
- HTML export for shareable reports

## Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [Example Output](#example-output)
- [Core Features](#core-features)
- [CLI Reference](#cli-reference)
- [Interactive Mode](#interactive-mode)
- [Python API](#python-api)
- [Data Sources](#data-sources)
- [Architecture](#architecture)
- [Testing](#testing)
- [Configuration](#configuration)
- [Roadmap](#roadmap)
- [License](#license)

## Installation

### Requirements

- Python 3.11+

### Install from source

```bash
git clone https://github.com/abhilashpanda04/finscope.git
cd finscope
uv sync
```

### Install with pip

```bash
pip install -e .
```

### Development install

```bash
uv sync --dev
# or
pip install -e ".[dev]"
```

## Quick Start

### Single-stock overview

```bash
finscope AAPL
```

### Interactive dashboard

```bash
finscope AAPL -i
```

### Valuation and risk

```bash
finscope AAPL valuate
finscope AAPL risk 1y
```

### Compare multiple stocks

```bash
finscope compare AAPL MSFT GOOGL
```

### Explore funds

```bash
finscope funds
```

### Export an HTML report

```bash
finscope export AAPL
```

## Example Output

### Overview

```text
$ finscope AAPL

Loading AAPL...

╭──────────────────────────── Company Overview ────────────────────────────╮
│ Apple Inc. (AAPL)                                                        │
│ Technology / Consumer Electronics                                        │
│ Exchange: NMS  |  Currency: USD                                          │
│                                                                            │
│ USD 230.45  +1.23%                                                       │
╰───────────────────────────────────────────────────────────────────────────╯

  3-Month Trend: ▁▂▃▄▅▆▇█▇▆▅▄▅▆▇

┏━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━┓
┃ Metric               ┃ Value         ┃ Metric               ┃ Value         ┃
┡━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━┩
┃ Market Cap           ┃ $3.42T        ┃ P/E Ratio            ┃ 31.2          ┃
┃ Forward P/E          ┃ 28.7          ┃ ROE                  ┃ 147.3%        ┃
└──────────────────────┴───────────────┴──────────────────────┴───────────────┘
```

### Risk profile

```text
$ finscope AAPL risk 1y

Computing risk profile for AAPL (1y)...

──────────────────────────── Risk Profile: AAPL ────────────────────────────
  ████████████░░░░░░░░ 63/100  Moderate Risk

  Risk Factors
    • Elevated volatility vs market
    • Drawdown exceeds defensive threshold

────────────── Volatility  (src: price history — daily returns) ─────────────
  Annual Volatility:   27.4%  (High)
  30D Volatility:      24.1%
  90D Volatility:      28.8%

──────────── Risk-Adjusted Returns  (src: price history vs risk-free rate) ──
  Annual Return:       +18.6%
  Sharpe Ratio:        0.54
  Sortino Ratio:       0.82
```

### Interactive dashboard

```text
$ finscope AAPL -i

╭──────────────────────── finscope dashboard ─────────────────────────╮
│ Apple Inc.                 USD 230.45            Mkt Cap: $3.42T    │
│ Technology | Hardware      +1.23%               P/E Ratio: 31.2     │
╰──────────────────────────────────────────────────────────────────────╯

Select an option:
  Fundamentals
    ▸ Company Overview
    ▸ Key Ratios
    ▸ Price History & Trend
  Financial Statements
    ▸ Income Statement
    ▸ Balance Sheet
    ▸ Cash Flow Statement
  Advanced Analysis
    ▸ Valuation
    ▸ Risk Profile
    ▸ Dividend Analysis
```

### Funds

```text
$ finscope funds

╭────────────────────────── finscope funds ───────────────────────────╮
│ Mutual Fund & ETF Explorer                                          │
│ Browse curated popular lists or search directly via market sources  │
╰──────────────────────────────────────────────────────────────────────╯

Select a category:
  Indian Funds
    ▸ Indian Mutual Funds (MFAPI.in)
  Global Curated
    ▸ Popular US Funds
    ▸ Global ETFs (LSE)
    ▸ Fixed Income / Bond ETFs
```

## Core Features

### Equity and market research

- Company overview with price snapshot and sparkline
- Key ratios and operating metrics
- Historical OHLCV price data across standard periods
- Recent news and analyst recommendations
- Major holders and ownership breakdown

### Financial statements and filings

- Income statement, balance sheet, and cash flow views
- SEC EDGAR XBRL financial extraction
- Recent SEC filings
- Insider transaction tracking

### Analytics

- Valuation models
  - Graham Number
  - Discounted Cash Flow
  - PEG fair value
  - Relative valuation
  - Piotroski F-Score
  - Altman Z-Score
- Risk analytics
  - Volatility
  - Value at Risk and Conditional VaR
  - Max drawdown
  - Sharpe, Sortino, and Calmar ratios
  - Beta and correlation versus market
- Dividend analysis and reinvestment views
- Earnings trend and surprise analysis
- Peer comparison
- S&P 500 screening

### Funds and portfolio workflows

- Global ETF and fund snapshot views
- Fund risk and rolling-return analysis
- Indian mutual fund search and NAV history
- Persistent watchlist
- Portfolio tracking and summary metrics

### Output

- Interactive terminal dashboard mode
- Rich tables, rules, sparklines, and formatted panels
- HTML report export
- Programmatic Python API

## CLI Reference

Command pattern:

```text
finscope <ticker> <command> [options]
```

### Core commands

| Command | Example | Description |
| :--- | :--- | :--- |
| default overview | `finscope AAPL` | Quick company overview |
| ratios | `finscope AAPL ratios` | Key financial ratios |
| price | `finscope AAPL price 1y` | Historical price table |
| financials | `finscope AAPL financials` | Income statement |
| balance-sheet | `finscope AAPL balance-sheet` | Balance sheet |
| cashflow | `finscope AAPL cashflow` | Cash flow statement |
| news | `finscope AAPL news` | Recent headlines |
| analysts | `finscope AAPL analysts` | Analyst recommendations |
| holders | `finscope AAPL holders` | Ownership breakdown |
| sec-financials | `finscope AAPL sec-financials` | SEC XBRL financials |
| sec-filings | `finscope AAPL sec-filings` | Recent SEC filings |
| insiders | `finscope AAPL insiders` | Insider transaction history |
| valuate | `finscope AAPL valuate` | Composite valuation models |
| risk | `finscope AAPL risk 1y` | Risk profile and downside metrics |
| dividends | `finscope AAPL dividends` | Dividend profile and history |
| earnings | `finscope AAPL earnings` | Earnings trend and surprise history |
| peers | `finscope AAPL peers` | Peer discovery and comparison |
| export | `finscope export AAPL` | HTML report export |

### Workflow commands

| Command | Example | Description |
| :--- | :--- | :--- |
| compare | `finscope compare AAPL MSFT GOOGL` | Side-by-side stock comparison |
| watchlist | `finscope watchlist AAPL TSLA NVDA` | Quick watchlist table |
| watch | `finscope watch add AAPL MSFT` | Persistent watchlist management |
| portfolio | `finscope portfolio add AAPL 50 142.50` | Portfolio tracking |
| screen | `finscope screen "pe < 15"` | S&P 500 screener |
| funds | `finscope funds` | Mutual fund and ETF explorer |
| interactive | `finscope AAPL -i` | Dashboard mode |

### Supported price periods

```text
1d  5d  1mo  3mo  6mo  1y  2y  5y  10y  ytd  max
```

## Interactive Mode

Interactive mode provides a grouped terminal dashboard for:

- overview and market data
- statements and filings
- advanced analysis
- comparison and screening
- watchlist, portfolio, and funds

Launch with:

```bash
finscope AAPL -i
```

Or start without a ticker:

```bash
finscope -i
```

## Python API

`finscope` is also available as a Python library.

### Stock research

```python
import finscope

aapl = finscope.stock("AAPL")

info = aapl.info
ratios = aapl.ratios
history = aapl.price_history("1y")
news = aapl.news
filings = aapl.sec_filings(count=10)

valuation = aapl.valuate()
risk = aapl.risk(period="1y")
```

### Comparison

```python
results = finscope.compare("AAPL", "MSFT", "GOOGL")
```

### Funds

```python
vwrl = finscope.fund("VWRL.L")
info = vwrl.info
returns = vwrl.returns
risk = vwrl.risk("1y")
analysis = vwrl.analyze()
```

## Data Sources

`finscope` uses different providers for different data classes.

| Source | Role | Used for |
| :--- | :--- | :--- |
| **SEC EDGAR** | Primary official source | US XBRL financials, filings, insider trades |
| **Yahoo Finance** | Secondary market-data source | Prices, ratios, analyst sentiment, news, global ETFs/funds |
| **MFAPI.in** | Primary source for Indian funds | Indian mutual fund metadata and NAV histories |

### Sourcing policy

- Official filing data is preferred where available
- Yahoo Finance is used as a broad-coverage market-data layer
- Terminal views include source attribution
- Missing or weak source coverage falls back gracefully rather than failing hard

### Note on trust and coverage

Yahoo Finance is convenient and broad, but it should not be treated as the sole trust anchor for every field. For high-trust US fundamentals, `finscope` prefers SEC EDGAR where possible. The current architecture also makes it straightforward to add alternative or premium providers in the future.

## Architecture

```text
src/finscope/
├── cli.py                  CLI entry point and interactive dashboard
├── stock.py                High-level Stock and Fund facades
├── services/               Orchestration layer over providers
├── providers/              Data-source adapters
├── risk/                   Risk models and computations
├── valuation/              Valuation models and verdicts
├── fund_analysis/          Fund analysis engines
├── ui/                     Rich renderers, formatters, builders
├── models.py               Shared typed data models
├── exceptions.py           Exception hierarchy
└── config.py               Runtime configuration
```

### Design choices

| Pattern | Usage |
| :--- | :--- |
| Strategy | Swap data providers without changing callers |
| Facade | Expose simple service interfaces over multiple providers |
| Builder | Standardize Rich table creation |
| Command-style CLI actions | Keep menu actions modular and testable |
| Typed dataclasses | Keep output structures explicit and predictable |

## Testing

Run the default suite:

```bash
pytest
```

Run integration tests:

```bash
pytest -m integration -v
```

Run with coverage:

```bash
pytest --cov=finscope --cov-report=term-missing
```

Recommended practice:

- use unit and smoke tests for routine local development
- run integration tests when changing providers or network behavior
- validate CLI rendering after changing menus or output models

## Configuration

### Environment variables

| Variable | Default | Purpose |
| :--- | :--- | :--- |
| `SEC_EDGAR_EMAIL` | `finscope-user@example.com` | Contact email in SEC EDGAR User-Agent |

Example:

```bash
export SEC_EDGAR_EMAIL=you@example.com
```

## Roadmap

Good next steps that fit the current architecture include:

- additional premium market-data providers
- macro and rates dashboards
- options and volatility workflows
- benchmark-relative fund analytics
- portfolio stress testing
- broader official-source replacement for third-party fields

## License

MIT

```text
finscope
Terminal-native financial research.
Built for speed. Structured for analysis. Sourced with traceability.
```