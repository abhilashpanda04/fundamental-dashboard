"""Screener module for finding stocks that match fundamental criteria."""

from finscope.screener.engine import ScreenerResult, get_sp500_tickers, screen

__all__ = ["screen", "ScreenerResult", "get_sp500_tickers"]
