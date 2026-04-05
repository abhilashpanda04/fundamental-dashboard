"""Custom exceptions for finscope.

All exceptions inherit from ``FinScopeError`` so callers can catch the
entire hierarchy with a single ``except FinScopeError`` clause, or be
selective by catching a specific subclass.
"""

from __future__ import annotations

__all__ = [
    "FinScopeError",
    "TickerNotFoundError",
    "DataFetchError",
    "CIKNotFoundError",
    "FundNotFoundError",
    "InvalidPeriodError",
]


class FinScopeError(Exception):
    """Base exception for every error raised by finscope."""


# Backward-compatible alias so any code that caught the old name still works.
DashboardError = FinScopeError


class TickerNotFoundError(FinScopeError):
    """Raised when a ticker symbol cannot be resolved by a provider."""

    def __init__(self, symbol: str) -> None:
        self.symbol = symbol
        super().__init__(f"Ticker not found: '{symbol}'")


class DataFetchError(FinScopeError):
    """Raised when a provider fails to retrieve data (network / API error)."""

    def __init__(self, provider: str, reason: str) -> None:
        self.provider = provider
        self.reason = reason
        super().__init__(f"[{provider}] Data fetch failed: {reason}")


class CIKNotFoundError(FinScopeError):
    """Raised when the SEC CIK number cannot be resolved for a ticker."""

    def __init__(self, symbol: str) -> None:
        self.symbol = symbol
        super().__init__(f"SEC CIK not found for ticker: '{symbol}'")


class FundNotFoundError(FinScopeError):
    """Raised when a mutual fund cannot be found by scheme code or name."""

    def __init__(self, identifier: str) -> None:
        self.identifier = identifier
        super().__init__(f"Fund not found: '{identifier}'")


class InvalidPeriodError(FinScopeError):
    """Raised when an unsupported time period string is supplied."""

    VALID_PERIODS = ("1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max")

    def __init__(self, period: str) -> None:
        self.period = period
        super().__init__(
            f"Invalid period '{period}'. Valid options: {', '.join(self.VALID_PERIODS)}"
        )
