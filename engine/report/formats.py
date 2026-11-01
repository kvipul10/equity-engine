"""Number formats for the human-readable report (deterministic; one place so HTML, XLSX and findings agree)."""
from __future__ import annotations

import math
from typing import Optional

from .core import fmt

MINUS = "−"


def _num(v) -> Optional[float]:
    if v is None:
        return None
    try:
        v = float(v)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(v) or math.isinf(v) else v


def signed(s: str) -> str:
    """Typographic minus for negative numbers in prose."""
    return s.replace("-", MINUS, 1) if s.startswith("-") else s


def value(v, unit: str) -> str:
    """A level: 53.0%, 1.20x, 93 days, Rs 1,234 cr. Days of sales are shown in days."""
    v = _num(v)
    if v is None:
        return "n/a"
    if unit == "days_of_sales":
        return f"{v * 365:.0f} days"
    if unit == "inr":
        return f"Rs {v:,.0f}"
    if unit == "ratio":
        return f"{v:.2f}"
    if unit == "score":
        return f"{v:.2f}"
    if unit == "num":
        return f"{v:,.2f}" if abs(v) < 1000 else f"{v:,.0f}"
    return signed(fmt(v, unit))


def delta(d, unit: str) -> str:
    """A change between two levels: percentages move in points (pts), not per cent."""
    d = _num(d)
    if d is None:
        return "n/a"
    if unit in ("pct", "pp"):
        s = f"{d * 100:+.1f} pts"
    elif unit == "x":
        s = f"{d:+.2f}x"
    elif unit == "days":
        s = f"{d:+.0f} days"
    elif unit == "days_of_sales":
        s = f"{d * 365:+.0f} days"
    elif unit == "inr_cr":
        s = f"{d:+,.0f} cr"
    elif unit == "inr":
        s = f"Rs {d:+,.0f}"
    elif unit == "count":
        s = f"{d:+,.0f}"
    else:
        s = f"{d:+.2f}"
    return signed(_unsign_zero(s))


def _unsign_zero(s: str) -> str:
    """'+0.0 pts' / '-0.0 pts' -> '0.0 pts': a change that rounds to zero has no direction."""
    body = s[1:] if s[:1] in "+-" else s
    digits = [c for c in body if c.isdigit()]
    return body if digits and all(c == "0" for c in digits) else s


def slope(s, unit: str) -> str:
    """Trend slope per year in the metric's unit (pts for percentages; counts to one decimal)."""
    v = _num(s)
    if unit == "count" and v is not None:
        return signed(_unsign_zero(f"{v:+.1f}"))
    return delta(s, unit)


def pct(v, digits: int = 0) -> str:
    """A share or percentile: 0.7 -> 70%."""
    v = _num(v)
    if v is None:
        return "n/a"
    return signed(f"{v * 100:.{digits}f}%")


def ordinal(p) -> str:
    """Percentile 0.1 -> '10th'."""
    v = _num(p)
    if v is None:
        return "n/a"
    n = int(round(v * 100))
    suf = "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suf}"


def crore(v) -> str:
    v = _num(v)
    return "n/a" if v is None else signed(f"{v:,.0f}")
