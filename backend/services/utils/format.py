"""The only permitted currency and date display functions (AD-13).

  - ``formatINR(amount: float) -> str``  Indian number grouping, e.g. ``₹1,25,000``
  - ``formatDate(iso: str) -> str``      ISO date to ``"30 Jun 2026"``

Direct f-string formatting of currency/dates in components or State handlers is not
acceptable. The prototype's ``shared/format.js`` is the JS twin — keep output identical
for valid input. Deliberate divergence: these helpers **raise ``ValueError``** on invalid
input (AC #6) where the JS silently coerces.

The ``float`` parameter of ``formatINR`` is the sanctioned *display-only* float boundary
(AC #7). All money *arithmetic* in ``services/`` uses ``Decimal`` — never these helpers.
Indian grouping is implemented by hand (no ``locale``/``babel`` dependency) so output is
identical on any machine.
"""
from __future__ import annotations

import math
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

_MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def _group_indian(digits: str) -> str:
    """Group a run of digits Indian-style: last 3, then pairs (``12500000`` -> ``1,25,00,000``)."""
    if len(digits) <= 3:
        return digits
    last3 = digits[-3:]
    rest = digits[:-3]
    parts: list[str] = []
    while len(rest) > 2:
        parts.insert(0, rest[-2:])
        rest = rest[:-2]
    if rest:
        parts.insert(0, rest)
    return ",".join(parts) + "," + last3


def formatINR(amount: float | Decimal) -> str:
    """Format a number as Indian Rupees with Indian digit grouping.

    ``formatINR(125000.0) -> "₹1,25,000"``; ``formatINR(-640) -> "-₹640"``;
    ``formatINR(0) -> "₹0"``. Whole rupees only (rounds half-up); the sign precedes ``₹``.

    Accepts ``float`` (the AC's display type) or ``Decimal`` (the engine's money type, AD-8),
    so a call site may hand it an engine value directly without a lossy pre-conversion.

    Raises:
        ValueError: if ``amount`` is not a finite number (``str``, ``None``, ``bool``,
            ``NaN``, ``Inf`` all rejected) — display must never fabricate ``₹0`` from junk.
    """
    if isinstance(amount, bool) or not isinstance(amount, (int, float, Decimal)):
        raise ValueError(f"formatINR expects a number, got {type(amount).__name__}: {amount!r}")
    finite = amount.is_finite() if isinstance(amount, Decimal) else math.isfinite(amount)
    if not finite:
        raise ValueError(f"formatINR expects a finite number, got {amount!r}")

    rupees = int(Decimal(str(amount)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    sign = "-" if rupees < 0 else ""
    grouped = _group_indian(str(abs(rupees)))
    return f"{sign}₹{grouped}"


def formatDate(iso: str) -> str:
    """Format an ISO ``YYYY-MM-DD`` string as ``"30 Jun 2026"`` (day not zero-padded).

    Raises:
        ValueError: if ``iso`` is not a valid ISO calendar date — a non-string, an empty
            string, the wrong shape/separator, or an impossible date like ``2023-02-29``.
            (``datetime.strptime`` raises ``ValueError`` for invalid calendar dates.)
    """
    if not isinstance(iso, str) or not iso:
        raise ValueError(f"formatDate expects a non-empty ISO date string, got {iso!r}")
    d = datetime.strptime(iso, "%Y-%m-%d")
    return f"{d.day} {_MONTHS[d.month - 1]} {d.year}"
