"""Custom exceptions for the Fundamental Dashboard.

Provides a clear, typed exception hierarchy so callers can handle
specific failures without catching bare Exception.
"""


class DashboardError(Exception):
    """Base exception for every error raised by this application."""


class TickerNotFoundError(DashboardError):
    """Raised when a ticker symbol cannot be resolved by a provider."""

    def __init__(self, symbol: str) -> None:
        self.symbol = symbol
        super().__init__(f"Ticker not found: '{symbol}'")


class DataFetchError(DashboardError):
    """Raised when a provider fails to retrieve data (network / API error)."""

    def __init__(self, provider: str, reason: str) -> None:
        self.provider = provider
        self.reason = reason
        super().__init__(f"[{provider}] Data fetch failed: {reason}")


class CIKNotFoundError(DashboardError):
    """Raised when the SEC CIK number cannot be resolved for a ticker."""

    def __init__(self, symbol: str) -> None:
        self.symbol = symbol
        super().__init__(f"SEC CIK not found for ticker: '{symbol}'")


class FundNotFoundError(DashboardError):
    """Raised when a mutual fund cannot be found by scheme code or name."""

    def __init__(self, identifier: str) -> None:
        self.identifier = identifier
        super().__init__(f"Fund not found: '{identifier}'")


class InvalidPeriodError(DashboardError):
    """Raised when an unsupported time period string is supplied."""

    VALID_PERIODS = ("1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max")

    def __init__(self, period: str) -> None:
        self.period = period
        super().__init__(
            f"Invalid period '{period}'. Valid options: {', '.join(self.VALID_PERIODS)}"
        )
