# Fundamental Dashboard

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> A terminal-based stock fundamental analysis dashboard — no browser, no API keys, just your terminal.

---

## What This Does

Type a ticker symbol and get instant access to:

- **Company Overview** — Name, sector, industry, current price, business description, and a 3-month ASCII sparkline chart
- **Key Financial Ratios** — P/E, PEG, Price/Book, ROE, Debt/Equity, margins, and 20+ other metrics
- **Price History** — OHLCV data for any period (1 day to max), color-coded green/red, with an inline sparkline chart
- **Income Statement / Balance Sheet / Cash Flow** — Annual financial statements in a formatted table
- **Analyst Recommendations** — Buy/Sell/Hold ratings rendered as a color-coded bar chart
- **Major Holders** — Top institutional holders (Vanguard, BlackRock, etc.) with share counts
- **Stock Comparison** — Side-by-side ratio comparison of multiple tickers with trend sparklines
- **Watchlist** — Compact multi-ticker table with price, change, market cap, P/E, and trend
- **News** — Latest headlines with publisher and links
- **Export to HTML** — Save the full report as a shareable HTML file

All data is pulled live from Yahoo Finance. No API keys required.

---

## Why I Built This

Most stock dashboards require a browser, API keys, or paid subscriptions. I wanted something I could run directly in my terminal while working — no context switching, no distractions.

The original version of this project was a Streamlit app that depended on deprecated libraries (`fbprophet`) and paid APIs (IEX Cloud, Alpha Vantage) with hardcoded keys. I rebuilt it from scratch as a terminal-first application using `rich` for rendering and `yfinance` for free, reliable data.

---

## Demo

### Company Overview with Sparkline
```text
╭──────────────────── Company Overview ────────────────────╮
│ Apple Inc.  (AAPL)                                       │
│ Technology / Consumer Electronics                        │
│ Exchange: NMS  |  Currency: USD                          │
│ USD 255.92  +0.11%                                       │
╰──────────────────────────────────────────────────────────╯
  3-Month Trend: ▅▄▃▃▄▃▂▁▁▁▃▃▃▆▇█▇▇▄▄▄▅▆▇▄▅▄▄▃▄▃▂▁▂▂▁▁▃  -4.3%
```

### Analyst Recommendations
```text
  Total Analysts: 48

    Strong Buy  ██████ 6 (12%)
           Buy  ██████████████████████████ 25 (52%)
          Hold  ███████████████ 15 (31%)
          Sell  █ 1 (2%)
   Strong Sell  █ 1 (2%)
```

### Stock Comparison with Sparklines
```text
    AAPL  ▅▄▃▃▄▃▂▁▁▁▃▃▆▇█▇▇▄▄▅▆▇▄▅▄▄▃▄▃▂▁▂▁▁▃  -4.3%
    MSFT  ▇▇█▇▇▆▆▅▆▇▇▅▄▃▃▃▃▃▂▃▃▃▃▃▃▃▂▂▁▁▁▁▁▁  -21.7%
   GOOGL  ▅▅▆▆▇▇▆▆▆▆▇▇█▆▆▄▄▃▅▄▄▄▃▃▄▄▃▄▃▂▁▁▂▃   -6.0%

╭────────────────── Side-by-Side Comparison ──────────────────╮
│ Metric         │         AAPL │         MSFT │        GOOGL │
├────────────────┼──────────────┼──────────────┼──────────────┤
│ P/E Ratio      │        32.35 │        23.37 │        27.39 │
│ Profit Margin  │        27.0% │        39.0% │        32.8% │
│ ROE            │       152.0% │        34.4% │        35.7% │
│ ...            │          ... │          ... │          ... │
╰────────────────┴──────────────┴──────────────┴──────────────╯
```

---

## Project Structure

```text
fundamental-dashboard/
├── src/dashboard/
│   ├── cli.py          ← Interactive menu loop (13 options)
│   ├── data.py         ← Yahoo Finance data fetching
│   └── ui.py           ← Rich rendering (sparklines, tables, bars, panels, export)
├── pyproject.toml
├── .gitignore
└── README.md
```

---

## Getting Started

### Installation

```bash
git clone https://github.com/abhilashpanda04/fundamental-dashboard.git
cd fundamental-dashboard

uv sync
source .venv/bin/activate
```

### Usage

```bash
# Interactive mode
dashboard

# Pass a ticker directly
dashboard AAPL
```

### Menu Options

```text
 [ 1] Company Overview
 [ 2] Key Ratios
 [ 3] Price History (with sparkline)
 [ 4] Income Statement
 [ 5] Balance Sheet
 [ 6] Cash Flow
 [ 7] News
 [ 8] Analyst Recommendations
 [ 9] Major Holders
 [10] Compare Stocks
 [11] Watchlist
 [12] Export Report to HTML
 [13] Change Ticker
 [ 0] Exit
```

---

## Tech Stack

- **Data Source**: [Yahoo Finance](https://finance.yahoo.com/) via `yfinance` (free, no API key)
- **Terminal UI**: [Rich](https://github.com/Textualize/rich) (tables, panels, sparklines, bar charts, HTML export)
- **Package Management**: [uv](https://github.com/astral-sh/uv)

---

## Contributing and Feedback

If you have ideas for new views (options chains, insider trades, earnings calendar), feel free to open an issue or PR.

## About Me

**Abhilash Kumar Panda**
- Email: abhilashk.isme1517@gmail.com
- LinkedIn: [Abhilash Kumar Panda](https://www.linkedin.com/in/abhilash-kumar-panda/)
- Portfolio: [abhilashpanda04.github.io](https://abhilashpanda04.github.io/Portfolio_site/)
- GitHub: [@abhilashpanda04](https://github.com/abhilashpanda04)

---
*If you found this useful, please consider giving the repo a star.*
