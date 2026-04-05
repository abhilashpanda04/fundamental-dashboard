"""Application configuration — Singleton pattern via module-level instance.

All configuration is centralised here. External code should import the
``config`` object and read attributes; never hard-code values elsewhere.

Environment variables:
    SEC_EDGAR_EMAIL: Contact e-mail sent in SEC EDGAR User-Agent header.
                     Defaults to a generic placeholder when not set.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

__all__ = ["Config", "config"]


@dataclass
class Config:
    """Immutable (by convention) application configuration.

    The module-level ``config`` singleton is created with defaults derived
    from environment variables so that tests can override them easily.
    """

    # ── SEC EDGAR ────────────────────────────────────────────────────────
    sec_edgar_email: str = field(
        default_factory=lambda: os.environ.get(
            "SEC_EDGAR_EMAIL", "finscope-user@example.com"
        )
    )

    # ── Network ──────────────────────────────────────────────────────────
    request_timeout: int = 15
    """Seconds to wait before a remote request times out."""

    # ── Display ──────────────────────────────────────────────────────────
    sparkline_width: int = 40
    """Character width used when rendering ASCII sparklines."""

    max_news_items: int = 8
    """Maximum number of news headlines to display."""

    max_price_rows: int = 15
    """Maximum rows shown in the price-history table."""

    max_institutional_holders: int = 10
    """Maximum rows shown in the institutional-holders table."""

    # ── Defaults ─────────────────────────────────────────────────────────
    default_price_period: str = "1mo"
    """Default period for price-history requests."""

    default_sparkline_period: str = "3mo"
    """Default period used when rendering the header sparkline."""

    # ── Derived properties ───────────────────────────────────────────────
    @property
    def sec_user_agent(self) -> str:
        """Full User-Agent string required by the SEC fair-access policy."""
        return f"Finscope {self.sec_edgar_email}"

    @property
    def sec_headers(self) -> dict[str, str]:
        """Ready-to-use headers dict for SEC EDGAR HTTP requests."""
        return {
            "User-Agent": self.sec_user_agent,
            "Accept-Encoding": "gzip, deflate",
        }


# ── Module-level singleton (Singleton Pattern) ────────────────────────────────
config = Config()
