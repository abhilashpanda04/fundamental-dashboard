"""Screener engine for filtering stocks based on fundamental criteria."""

from __future__ import annotations

import ast
import concurrent.futures
import logging
from dataclasses import dataclass
from typing import Any

import pandas as pd

import finscope
from finscope.exceptions import TickerNotFoundError

logger = logging.getLogger(__name__)

__all__ = ["screen", "ScreenerResult", "get_sp500_tickers"]


@dataclass
class ScreenerResult:
    """A single stock that matched the screener criteria."""
    symbol: str
    metrics: dict[str, Any]


def get_sp500_tickers() -> list[str]:
    """Fetch the current S&P 500 tickers from Wikipedia."""
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    # Try parsers in order: lxml (fastest) → html5lib → html.parser (stdlib, always available)
    for flavor in ("lxml", "html5lib", "html.parser"):
        try:
            tables = pd.read_html(url, flavor=flavor)
            df = tables[0]
            tickers = df["Symbol"].str.replace(".", "-", regex=False).tolist()
            logger.debug(f"S&P 500 tickers fetched via {flavor} ({len(tickers)} symbols)")
            return tickers
        except ImportError:
            continue          # parser not installed, try next
        except Exception as e:
            logger.warning(f"Could not fetch S&P 500 tickers (flavor={flavor}): {e}")
            break
    return []


def _fetch_stock_metrics(symbol: str) -> dict[str, Any] | None:
    """Fetch key metrics for a single stock for screening."""
    try:
        s = finscope.stock(symbol)
        info = s.info
        if not info:
            return None
            
        ratios = s.ratios
        
        metrics = {
            "symbol": symbol.upper(),
            "sector": info.get("sector", ""),
            "industry": info.get("industry", ""),
            "market_cap": ratios.market_cap,
            "pe": ratios.pe_ratio,
            "forward_pe": ratios.forward_pe,
            "pb": ratios.price_to_book,
            "ps": ratios.price_to_sales,
            "dividend_yield": (ratios.dividend_yield * 100) if ratios.dividend_yield else 0.0,
            "roe": (ratios.return_on_equity * 100) if ratios.return_on_equity else None,
            "roa": (ratios.return_on_assets * 100) if ratios.return_on_assets else None,
            "debt_to_equity": ratios.debt_to_equity,
            "current_price": info.get("currentPrice") or info.get("regularMarketPrice"),
        }
        return metrics
    except Exception:
        return None

def screen(
    query: str | None = None,
    universe: list[str] | None = None,
    max_workers: int = 20,
    **kwargs,
) -> list[ScreenerResult]:
    """Screen stocks based on financial criteria.
    
    Args:
        query: String DSL query (e.g., "pe < 20 and roe > 15 and sector == 'Technology'")
        universe: List of tickers to screen. Defaults to S&P 500.
        max_workers: Number of threads to use for data fetching.
        **kwargs: Filter criteria as kwargs, e.g., pe=("<", 20), roe=(">", 15)
        
    Returns:
        List of :class:`ScreenerResult` objects that match the criteria.
    """
    if universe is None:
        universe = get_sp500_tickers()
        
    if not universe:
        return []

    # Combine kwargs into a query string if no query provided
    filters = []
    for key, val in kwargs.items():
        if isinstance(val, tuple) and len(val) == 2:
            op, target = val
            if isinstance(target, str):
                filters.append(f"{key} {op} '{target}'")
            else:
                filters.append(f"{key} {op} {target}")
        else:
            if isinstance(val, str):
                filters.append(f"{key} == '{val}'")
            else:
                filters.append(f"{key} == {val}")
                
    combined_query = query
    if filters:
        kwargs_query = " and ".join(filters)
        if combined_query:
            combined_query = f"({combined_query}) and ({kwargs_query})"
        else:
            combined_query = kwargs_query

    all_metrics = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_symbol = {executor.submit(_fetch_stock_metrics, sym): sym for sym in universe}
        
        for future in concurrent.futures.as_completed(future_to_symbol):
            metrics = future.result()
            if metrics:
                all_metrics.append(metrics)
                
    if not all_metrics:
        return []
        
    df = pd.DataFrame(all_metrics)
    
    # Apply query using pandas
    if combined_query:
        try:
            # fillna to avoid issues with missing data in comparisons
            df = df.query(combined_query)
        except Exception as e:
            logger.error(f"Invalid screener query: {e}")
            return []
            
    # Sort by market cap by default if available
    if "market_cap" in df.columns:
        df = df.sort_values("market_cap", ascending=False)
        
    results = []
    for _, row in df.iterrows():
        r_dict = row.dropna().to_dict()
        results.append(ScreenerResult(symbol=r_dict.pop("symbol"), metrics=r_dict))
        
    return results
