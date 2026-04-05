```
 _____ _       ____
|  ___(_)_ __ / ___|  ___ ___  _ __   ___
| |_  | | '_ \\___ \ / __/ _ \| '_ \ / _ \
|  _| | | | | |___) | (_| (_) | |_) |  __/
|_|   |_|_| |_|____/ \___\___/| .__/ \___|
                               |_|    v1.0.0
```

**Terminal-native financial research. Stocks, ETFs, mutual funds.**

FinScope pulls real-time and historical data from Yahoo Finance, SEC EDGAR,
and MFAPI.in -- no API keys, no browser, no spreadsheets. Everything renders
in your terminal via Rich tables, sparklines, and formatted reports.

```
$ finscope AAPL

  APPLE INC.  |  Technology  |  AAPL
  ----------------------------------------
  Price        $187.44   Change  +1.23%
  Market Cap   $2.87T    Beta    1.29
  52-Week      $143.90 - $199.62
  Sparkline    ___/^^^^\_/^^^^^
```

---

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [CLI Reference](#cli-reference)
- [Library API](#library-api)
- [Architecture](#architecture)
- [Testing](#testing)
- [Data Sources](#data-sources)
- [Configuration](#configuration)
- [License](#license)

---

## Features

```
CATEGORY              DESCRIPTION
--------------------  -----------------------------------------------------------
Stock Overview        Name, sector, price, live change %, 3-month sparkline
Key Ratios            P/E, Forward P/E, PEG, P/B, P/S, EV/EBITDA, margins,
                      ROE, debt/equity, beta, 52-week range
Price History         OHLCV table + ASCII sparkline for any period (1d to max)
Financial Statements  Income statement, balance sheet, cash flow (Yahoo Finance)
SEC EDGAR             XBRL financials (7 categories, 6 fiscal years),
                      recent filings browser, insider transactions
Analyst Consensus     Buy / Hold / Sell bar chart
Holders               Ownership breakdown + top institutional holders
Comparison            Side-by-side metrics for up to 10 tickers with sparklines
Watchlist             Compact multi-ticker monitoring table
Mutual Funds          37,500+ Indian funds (MFAPI.in) + global ETFs via Yahoo
HTML Export           One-command report with ratios and price history
```

---

## Installation

Requires Python 3.11+.

```bash
git clone https://github.com/abhilashpanda04/finscope.git
cd finscope
uv sync
```

Or with pip:

```bash
pip install -e .
```

For development and testing:

```bash
uv sync --dev
# or: pip install -e ".[dev]"
```

---

## Quick Start

Pull a stock overview in one command:

```bash
$ finscope AAPL
```

Compare multiple tickers side by side:

```bash
$ finscope compare AAPL MSFT GOOGL
```

Export a full HTML report:

```bash
$ finscope export AAPL -o apple_report.html
```

Launch the interactive research menu:

```bash
$ finscope AAPL -i
```

---

## CLI Reference

All commands follow the pattern `finscope <TICKER> <command> [options]`.

```
COMMAND               EXAMPLE                              OUTPUT
--------------------  -----------------------------------  -------------------------
(default)             finscope AAPL                        Stock overview + sparkline
ratios                finscope AAPL ratios                 Key financial ratios
price <period>        finscope AAPL price 1y               OHLCV + sparkline (1 year)
financials            finscope AAPL financials             Income statement
balance-sheet         finscope AAPL balance-sheet          Balance sheet
cashflow              finscope AAPL cashflow               Cash flow statement
news                  finscope AAPL news                   Recent headlines
analysts              finscope AAPL analysts               Analyst recommendations
holders               finscope AAPL holders                Major holders
sec-financials        finscope AAPL sec-financials         SEC EDGAR XBRL data
sec-filings           finscope AAPL sec-filings            Recent SEC filings
insiders              finscope AAPL insiders               Insider transactions
compare               finscope compare AAPL MSFT GOOGL    Side-by-side comparison
watchlist              finscope watchlist AAPL TSLA NVDA   Compact multi-ticker table
export                finscope export AAPL                 HTML report (aapl_report.html)
export -o <path>      finscope export AAPL -o out.html     Custom output path
funds                 finscope funds                       Mutual funds explorer
-i                    finscope AAPL -i                     Interactive menu mode
```

### Periods for price history

```
1d  5d  1mo  3mo  6mo  1y  2y  5y  10y  ytd  max
```

---

## Library API

FinScope exposes a typed Python API for programmatic use.

### Stock analysis

```python
import finscope

aapl = finscope.stock("AAPL")

# Ratios -- lazy-loaded, cached, typed
aapl.ratios.pe_ratio           # 28.5
aapl.ratios.market_cap         # 2_700_000_000_000
aapl.ratios.debt_to_equity     # 1.87

# Price history -- returns a pandas DataFrame
df = aapl.price_history("1y")
# columns: Open, High, Low, Close, Volume

# Sparkline data
aapl.sparkline                 # [100.0, 105.3, ...]

# News, financials, SEC data
aapl.news                      # list of article dicts
aapl.financials                # income statement DataFrame
aapl.sec_financials            # XBRL data from SEC EDGAR
aapl.insider_transactions      # Form 4 filings

# Export
aapl.export_html()             # writes aapl_report.html
```

### Multi-stock comparison

```python
# From a stock object
aapl.compare_with("MSFT", "GOOGL")    # list[ComparisonData]

# Standalone function
finscope.compare("AAPL", "MSFT")
```

### Fund analysis

```python
vwrl = finscope.fund("VWRL.L")
vwrl.info                      # fund metadata
vwrl.returns                   # historical returns
vwrl.sparkline                 # NAV sparkline data
```

---

## Architecture

```
src/finscope/
|
|-- exceptions.py              Typed exception hierarchy
|-- config.py                  Singleton Config (env-var aware)
|-- models.py                  Typed dataclasses (KeyRatios, ComparisonData, ...)
|
|-- stock.py                   Stock + Fund facade classes (library entry points)
|
|-- providers/                 Strategy pattern -- one class per data source
|   |-- base.py                  Abstract interfaces
|   |-- yahoo_provider.py       Yahoo Finance via yfinance
|   |-- sec_edgar_provider.py   SEC EDGAR XBRL + filings
|   +-- mfapi_provider.py       MFAPI.in (India) + Yahoo (global ETFs)
|
|-- services/                  Facade pattern -- orchestrate providers
|   |-- stock_service.py         All stock operations
|   +-- fund_service.py          All fund operations
|
|-- ui/                        Presentation layer
|   |-- formatters.py            Pure formatting functions
|   |-- builders.py              Builder pattern for Rich tables
|   +-- renderers.py             All render functions
|
+-- cli.py                     Direct subcommands + opt-in interactive menu (-i)
```

### Design decisions

```
PATTERN      LOCATION           RATIONALE
-----------  -----------------  -----------------------------------------------
Strategy     providers/         Swap data sources without touching callers
Facade       services/          Single clean API over complex provider logic
Builder      ui/builders.py     Eliminate repetitive Rich table boilerplate
Command      cli.py             Each action is independently testable, zero if/elif
Singleton    config.py          One source of truth for all runtime settings
```

---

## Testing

325 tests across three tiers. Unit and smoke tests run offline in under a second.

```bash
# Default: unit + smoke tests (no network, ~0.6s)
pytest

# Include live API integration tests
pytest -m integration -v

# With coverage report
pytest --cov=finscope --cov-report=term-missing
```

### Test breakdown

```
SUITE                  COUNT   NETWORK   PURPOSE
---------------------  ------  --------  ------------------------------------------
tests/smoke/           54      No        Imports, wiring, object construction
tests/unit/            244     No        All logic paths, fully mocked
tests/integration/     27      Yes       Real Yahoo / SEC EDGAR / MFAPI calls
```

---

## Data Sources

All data sources are free and require no API keys.

```
SOURCE                 DATA                                         COST
---------------------  -------------------------------------------  ---------
Yahoo Finance          Prices, ratios, financials, news, ETFs       Free
SEC EDGAR              XBRL financials, filings, insider trades     Free
MFAPI.in               37,500+ Indian mutual fund NAV histories     Free
```

- [Yahoo Finance](https://finance.yahoo.com)
- [SEC EDGAR](https://www.sec.gov/edgar)
- [MFAPI.in](https://www.mfapi.in)

SEC EDGAR requires a contact email in the User-Agent header per their
fair-access policy. FinScope provides a default but you should set your own.

---

## Configuration

```
VARIABLE             DEFAULT                        PURPOSE
-------------------  -----------------------------  --------------------------------
SEC_EDGAR_EMAIL      finscope-user@example.com      SEC EDGAR User-Agent contact
```

Set via environment:

```bash
export SEC_EDGAR_EMAIL=you@example.com
```

---

## License

MIT

---

```
finscope v1.0.0
terminal-native financial research
https://github.com/abhilashpanda04/finscope
```
