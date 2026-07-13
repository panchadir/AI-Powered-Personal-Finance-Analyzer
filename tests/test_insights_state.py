"""Tests for the Insights page state (finance_app/state/insights_state.py).

Focused on ``_parse_evidence`` — the one place the page reads *untrusted* text back out of the
DB (the ``insights.evidence`` JSON column) and turns it into what FR-8.2 requires on screen:
2–3 exact data points, real dates, real merchants, real amounts.

It is a ``staticmethod``, so it is exercised directly — no Reflex app, no session, no LLM.
The contract under test is that it is *total*: every malformed shape degrades to fewer lines
(or none) and never raises, because an insight's evidence block is a supporting detail and a
single bad row must not blank the whole Insights page.
"""
from __future__ import annotations

import json

import pytest

from finance_app.state.insights_state import (
    DEFAULT_ICON,
    PATTERN_ICONS,
    SEVERITY_LABELS,
    InsightsState,
)
from services.engine.insights import ALL_DETECTORS

parse = InsightsState._parse_evidence


def _pack(*points: tuple[str, str, str]) -> str:
    """Serialize exactly as ``insights_bridge._serialize_evidence`` does."""
    return json.dumps([{"date": d, "merchant": m, "amount": a} for d, m, a in points])


class TestParseEvidenceHappyPath:
    def test_formats_a_point_as_date_merchant_amount(self):
        assert parse(_pack(("2026-07-05", "Swiggy", "450.00"))) == ["5 Jul 2026 · Swiggy · ₹450"]

    def test_preserves_order_and_renders_every_point(self):
        raw = _pack(
            ("2026-07-05", "Swiggy", "450"),
            ("2026-07-06", "Zomato", "310"),
            ("2026-07-08", "Blinkit", "1250"),
        )
        assert parse(raw) == [
            "5 Jul 2026 · Swiggy · ₹450",
            "6 Jul 2026 · Zomato · ₹310",
            "8 Jul 2026 · Blinkit · ₹1,250",
        ]

    def test_amount_uses_indian_digit_grouping(self):
        assert parse(_pack(("2026-07-05", "Rent", "125000"))) == ["5 Jul 2026 · Rent · ₹1,25,000"]

    def test_amount_is_the_exact_figure_the_detector_cited_not_a_float_round_trip(self):
        """AD-8: money crosses the JSON boundary as a string and comes back a Decimal."""
        assert parse(_pack(("2026-07-05", "Swiggy", "0.5"))) == ["5 Jul 2026 · Swiggy · ₹1"]


class TestParseEvidenceIsTotal:
    """Every one of these must return a value, not raise — the page must still render."""

    @pytest.mark.parametrize(
        "raw",
        [
            "",  # column never written
            "not json at all",  # malformed
            "{}",  # JSON, but an object not a list
            '"a string"',  # JSON, but a scalar
            "null",
            "[]",  # empty pack
        ],
    )
    def test_unusable_payloads_yield_no_lines(self, raw):
        assert parse(raw) == []

    def test_skips_a_malformed_point_but_keeps_the_good_ones(self):
        raw = json.dumps(
            [
                {"date": "2026-07-05", "merchant": "Swiggy", "amount": "450"},
                {"date": "2026-02-30", "merchant": "Impossible", "amount": "1"},  # bad date
                {"date": "2026-07-06", "merchant": "Zomato", "amount": "not-a-number"},
                {"merchant": "NoDate", "amount": "10"},  # missing key
                "just a string",  # not even an object
                {"date": "2026-07-08", "merchant": "Blinkit", "amount": "1250"},
            ]
        )
        assert parse(raw) == ["5 Jul 2026 · Swiggy · ₹450", "8 Jul 2026 · Blinkit · ₹1,250"]

    def test_a_pack_of_only_malformed_points_yields_no_lines(self):
        raw = json.dumps([{"date": "nope", "merchant": "X", "amount": "y"}])
        assert parse(raw) == []


class TestSeverityLabels:
    @pytest.mark.parametrize("tier", ["critical", "important", "flexible"])
    def test_every_tier_the_engine_can_emit_has_a_label(self, tier):
        """The three ``Criticality`` values ``InsightCandidate.severity`` is documented to use."""
        assert SEVERITY_LABELS[tier]


class TestPatternIcons:
    def test_every_detector_has_its_own_icon(self):
        """The WDS prototype always supported a per-insight icon; we only ever sent it the
        fallback, so every card wore the same lightbulb and the feed read as one grey wall.
        A detector added without an icon would silently rejoin that wall."""
        for detector in ALL_DETECTORS:
            assert detector.pattern_name in PATTERN_ICONS, (
                f"{detector.pattern_name!r} has no icon -- its card falls back to the "
                "generic lightbulb and stops being visually distinguishable."
            )

    def test_icons_are_distinct_so_the_feed_is_scannable(self):
        icons = [PATTERN_ICONS[d.pattern_name] for d in ALL_DETECTORS]
        assert len(set(icons)) == len(icons), "two patterns share an icon"

    def test_an_unknown_pattern_still_gets_the_prototypes_default_not_a_blank(self):
        assert PATTERN_ICONS.get("Some future pattern", DEFAULT_ICON) == DEFAULT_ICON
        assert DEFAULT_ICON  # never renders an empty span
