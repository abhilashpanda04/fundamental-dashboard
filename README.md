# Fundamental Dashboard

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> A terminal-based stock fundamental analysis dashboard — no browser, no API keys, just your terminal.

---

## What This Does

Type a ticker symbol and get instant access to:

- **Company Overview** — Name, sector, industry, current price, and business description
- **Key Financial Ratios** — P/E, PEG, Price/Book, ROE, Debt/Equity, margins, and more
- **Price History** — OHLCV data for any period (1 day to max), color-coded green/red
- **Income Statement** — Annual revenue, net income, operating expenses
- **Balance Sheet** — Assets, liabilities, equity breakdown
- **Cash Flow** — Operating, investing, and financing cash flows
- **News** — Latest headlines with links to full articles

All data is pulled live from Yahoo Finance. No API keys required.

---

## Why I Built This

Most stock dashboards require a browser, API keys, or paid subscriptions. I wanted something I could run directly in my terminal while working — no context switching, no distractions.

The original version of this project was a Streamlit app that depended on deprecated libraries (`fbprophet`) and paid APIs (IEX Cloud, Alpha Vantage) with hardcoded keys. I rebuilt it from scratch as a terminal-first application using `rich` for rendering and `yfinance` for free, reliable data.

---

## Demo

```text
────────────────────── Fundamental Dashboard ──────────────────────

Enter a stock ticker (e.g., AAPL, TSLA, MSFT): AAPL

┌──────────────────── Company Overview ────────────────────┐
│ Apple Inc.  (AAPL)                                       │
│ Technology / Consumer Electronics                        │
│ Exchange: NMS  |  Currency: USD                          │
│                                                          │
│ USD 178.72  +1.34%                                       │
└──────────────────────────────────────────────────────────┘

───────────────────────── Menu ─────────────────────────
  [1] Company Overview
  [2] Key Ratios
  [3] Price History
  [4] Income Statement
  [5] Balance Sheet
  [6] Cash Flow
  [7] News
  [8] Change Ticker
  [0] Exit
```

---

## Project Structure

```text
fundamental-dashboard/
├── src/dashboard/
│   ├── cli.py          ← Interactive menu and main loop
│   ├── data.py         ← Yahoo Finance data fetching
│   └── ui.py           ← Rich rendering (tables, panels, colors)
├── pyproject.toml      ← Dependencies managed by uv
├── .gitignore
└── README.md
```

---

## Getting Started

### Installation

```bash
git clone https://github.com/abhilashpanda04/fundamental-dashboard.git
cd fundamental-dashboard

# Install with uv
uv sync

# Activate the environment
source .venv/bin/activate
```

### Usage

```bash
# Interactive mode — prompts for a ticker
dashboard

# Pass a ticker directly
dashboard AAPL

# Or run as a module
python -m dashboard.cli TSLA
```

Once inside the dashboard, use the numbered menu to navigate between views. Select `[8]` to switch to a different ticker, or `[0]` to exit.

---

## Tech Stack

- **Data Source**: [Yahoo Finance](https://finance.yahoo.com/) via `yfinance` (free, no API key)
- **Terminal UI**: [Rich](https://github.com/Textualize/rich) (tables, panels, colors, prompts)
- **Package Management**: [uv](https://github.com/astral-sh/uv)

---

## Contributing and Feedback

If you have ideas for new views (analyst ratings, insider trades, options chains), feel free to open an issue or PR.

## About Me

**Abhilash Kumar Panda**
- Email: abhilashk.isme1517@gmail.com
- LinkedIn: [Abhilash Kumar Panda](https://www.linkedin.com/in/abhilash-kumar-panda/)
- Portfolio: [abhilashpanda04.github.io](https://abhilashpanda04.github.io/Portfolio_site/)
- GitHub: [@abhilashpanda04](https://github.com/abhilashpanda04)

---
*If you found this useful, please consider giving the repo a star.*
