"""Pure formatting functions for the terminal UI.

All functions in this module are *pure* (no side effects, no I/O), which
makes them trivially unit-testable.  They accept raw values and return
Rich-markup strings or plain strings ready for display.
"""

from __future__ import annotations

from dashboard.config import config

# ── Sparkline ─────────────────────────────────────────────────────────────────

_SPARK_CHARS = "▁▂▃▄▅▆▇█"


def make_sparkline(values: list[float], width: int | None = None) -> str:
    """Render a Unicode block-character sparkline from a list of floats.

    Args:
        values: Ordered price / NAV series (oldest → newest).
        width:  Maximum character width. Defaults to ``config.sparkline_width``.

    Returns:
        A Rich-markup string with colour based on overall trend direction.
        Returns ``"[dim]No data[/dim]"`` when *values* has fewer than two points.
    """
    if not values or len(values) < 2:
        return "[dim]No data[/dim]"

    effective_width = width or config.sparkline_width

    # Downsample if the series is longer than the display width
    if len(values) > effective_width:
        step = len(values) / effective_width
        values = [values[int(i * step)] for i in range(effective_width)]

    mn, mx = min(values), max(values)
    rng = mx - mn if mx != mn else 1

    chars = "".join(
        _SPARK_CHARS[int((v - mn) / rng * (len(_SPARK_CHARS) - 1))]
        for v in values
    )

    color = "green" if values[-1] >= values[0] else "red"
    first = values[0] if values[0] != 0 else 1e-9  # guard against division by zero
    pct_change = ((values[-1] - first) / abs(first)) * 100

    return f"[{color}]{chars}[/{color}]  [{color}]{pct_change:+.1f}%[/{color}]"


# ── Number formatting ─────────────────────────────────────────────────────────

def format_number(value: float | None) -> str:
    """Format a raw float for display.

    - ``None``  → ``"[dim]N/A[/dim]"``
    - ≥ 1 B     → ``"$X.XXB"``
    - ≥ 1 M     → ``"$X.XXM"``
    - < 1       → four decimal places
    - otherwise → two decimal places
    """
    if value is None:
        return "[dim]N/A[/dim]"
    if not isinstance(value, (int, float)):
        return str(value)
    if abs(value) >= 1_000_000_000:
        return f"${value / 1_000_000_000:.2f}B"
    if abs(value) >= 1_000_000:
        return f"${value / 1_000_000:.2f}M"
    if abs(value) < 1:
        return f"{value:.4f}"
    return f"{value:.2f}"


def format_pct(value: float | None) -> str:
    """Format a decimal or percentage value with +/- colour.

    Values are expected to already be a percentage (e.g. ``1.5`` = 1.5 %).

    Returns:
        Rich-markup string in green (≥ 0) or red (< 0).
    """
    if value is None:
        return "[dim]N/A[/dim]"
    color = "green" if value >= 0 else "red"
    return f"[{color}]{value:+.2f}%[/{color}]"


def format_currency(value: float | None, currency: str = "") -> str:
    """Format a monetary value with B / M / K suffix.

    Args:
        value:    Raw amount (e.g. total AUM in USD).
        currency: Optional prefix (e.g. ``"USD"``, ``"₹"``).
    """
    if value is None:
        return "[dim]N/A[/dim]"
    try:
        v = float(value)
        prefix = f"{currency} " if currency else ""
        if abs(v) >= 1_000_000_000:
            return f"{prefix}{v / 1_000_000_000:.2f}B"
        if abs(v) >= 1_000_000:
            return f"{prefix}{v / 1_000_000:.2f}M"
        if abs(v) >= 1_000:
            return f"{prefix}{v / 1_000:.2f}K"
        return f"{prefix}{v:.4f}"
    except (TypeError, ValueError):
        return str(value)


def format_return(value: float | None) -> str:
    """Format a return percentage value with colour.

    Handles both fractional (0.015 → 1.5 %) and already-percentage (1.5)
    inputs by detecting whether the absolute value is < 1.
    """
    if value is None:
        return "[dim]N/A[/dim]"
    try:
        v = float(value)
        # If stored as a decimal fraction (e.g. 0.015), convert to percent
        if abs(v) < 1 and v != 0:
            v = v * 100
        color = "green" if v >= 0 else "red"
        return f"[{color}]{v:+.2f}%[/{color}]"
    except (TypeError, ValueError):
        return "[dim]N/A[/dim]"


def safe_float(val) -> float | None:
    """Coerce a possibly nested yfinance value to float or ``None``."""
    if val is None:
        return None
    if hasattr(val, "__iter__") and not isinstance(val, str):
        items = list(val)
        return float(items[0]) if items else None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None
