"""Story 1.2 · AC #4, #5, #6 — the only permitted currency/date display helpers (AD-13).

Output parity with the prototype JS twin (``prototypes/.../shared/format.js``) for the
happy path. One deliberate divergence: the JS coerces bad input to ``₹0`` / echoes the
raw string, but AC #6 requires the Python helpers to **raise ``ValueError``** on invalid
input — the correct Python contract.
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from services.utils.format import formatDate, formatINR


class TestFormatINR:
    def test_zero(self) -> None:
        assert formatINR(0) == "₹0"

    def test_lakh_grouping(self) -> None:
        # AC #4: 125000.0 -> ₹1,25,000 (Indian grouping: 3 then 2s)
        assert formatINR(125000.0) == "₹1,25,000"

    def test_thousands(self) -> None:
        assert formatINR(2840) == "₹2,840"

    def test_crore(self) -> None:
        # AC #6 edge: crore amount -> ₹1,00,00,000
        assert formatINR(10000000) == "₹1,00,00,000"

    def test_eighteen_lakh(self) -> None:
        assert formatINR(1800000) == "₹18,00,000"

    def test_negative_sign_before_symbol(self) -> None:
        # JS twin: -640 -> "-₹640" (sign precedes the ₹)
        assert formatINR(-640) == "-₹640"

    def test_sub_thousand(self) -> None:
        assert formatINR(500) == "₹500"

    def test_rounds_to_whole_rupees(self) -> None:
        # maximumFractionDigits: 0 parity — display is whole rupees.
        assert formatINR(2840.4) == "₹2,840"
        assert formatINR(2840.5) == "₹2,841"

    @pytest.mark.parametrize("bad", ["abc", None, "₹1,000", float("nan"), float("inf")])
    def test_invalid_raises_valueerror(self, bad) -> None:
        with pytest.raises(ValueError):
            formatINR(bad)

    def test_accepts_decimal_the_engine_money_type(self) -> None:
        # AD-8: engine money is Decimal; formatINR (the only display path, AD-13)
        # must render it directly without a lossy float() at the call site.
        assert formatINR(Decimal("125000")) == "₹1,25,000"
        assert formatINR(Decimal("2840.40")) == "₹2,840"  # rounds to whole rupees
        assert formatINR(Decimal("-640")) == "-₹640"

    @pytest.mark.parametrize("bad", [Decimal("NaN"), Decimal("Infinity")])
    def test_non_finite_decimal_raises_valueerror(self, bad) -> None:
        with pytest.raises(ValueError):
            formatINR(bad)


class TestFormatDate:
    def test_iso_to_long(self) -> None:
        # AC #5: "2026-06-30" -> "30 Jun 2026"
        assert formatDate("2026-06-30") == "30 Jun 2026"

    def test_day_not_zero_padded(self) -> None:
        assert formatDate("2026-06-05") == "5 Jun 2026"

    def test_january(self) -> None:
        assert formatDate("2026-01-01") == "1 Jan 2026"

    def test_december(self) -> None:
        assert formatDate("2025-12-31") == "31 Dec 2025"

    def test_valid_leap_day(self) -> None:
        # AC #6 edge: leap-year date is valid
        assert formatDate("2024-02-29") == "29 Feb 2024"

    @pytest.mark.parametrize(
        "bad",
        [
            "2023-02-29",  # Feb 29 in a non-leap year — invalid calendar date
            "2026-13-01",  # month out of range
            "2026-06-31",  # June has 30 days
            "not-a-date",
            "30-06-2026",  # wrong order / not ISO
            "2026/06/30",  # wrong separator
            "",
            None,
        ],
    )
    def test_invalid_raises_valueerror(self, bad) -> None:
        with pytest.raises(ValueError):
            formatDate(bad)
