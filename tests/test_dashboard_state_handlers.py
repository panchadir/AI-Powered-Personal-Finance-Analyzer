"""Coverage for ``finance_app/state/dashboard_state.py``.

Three layers:
  * The pure Plotly/axis helpers (``_nice_ceiling`` / ``_category_figure`` / ``_pace_figure`` …)
    are called directly.
  * The ``_apply_*`` display-mapping methods are called directly with constructed engine-shaped
    inputs so every formatting branch (income known/unknown, shortfall, buffer dented) is hit
    deterministically without depending on exact engine output.
  * ``load_dashboard`` is driven end-to-end over seeded transactions (``generate_briefing`` is
    monkeypatched so no network call happens), covering the empty / no-user / happy arms.
"""
from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

import pytest

import finance_app.state.dashboard_state as dash_mod
from finance_app.models import Transaction
from finance_app.state.dashboard_state import (
    DashboardState,
    EMPTY_HERO_COPY,
    WHY_FALLBACK,
    _category_figure,
    _empty_figure,
    _month_label,
    _nice_ceiling,
    _pace_figure,
)
from services.analytics import CategorySlice, MonthPoint
from tests.conftest import drive


# ---------------------------------------------------------------------------
# Pure figure/axis helpers
# ---------------------------------------------------------------------------

class TestPureHelpers:
    @pytest.mark.parametrize(
        "value, expected",
        [(0, 0.0), (-5, 0.0), (1, 1), (2, 2), (2.1, 2.5), (4, 5), (9, 10), (11, 20)],
    )
    def test_nice_ceiling(self, value, expected):
        assert _nice_ceiling(value) == expected

    def test_empty_figure_is_transparent(self):
        fig = _empty_figure()
        assert fig.layout.paper_bgcolor == "rgba(0,0,0,0)"

    def test_category_figure_labels_slices(self):
        fig = _category_figure([CategorySlice(category="Food", total=Decimal("1200"))])
        assert fig.data[0].labels == ("Food",)

    def test_month_label_formats(self):
        assert _month_label("2026-06") == "Jun 2026"

    def test_pace_figure_with_points_builds_ticks(self):
        fig = _pace_figure([MonthPoint(month="2026-06", total=Decimal("5000"))])
        assert list(fig.data[0].x) == ["Jun 2026"]

    def test_pace_figure_with_zero_total_has_no_ticks(self):
        fig = _pace_figure([MonthPoint(month="2026-06", total=Decimal("0"))])
        assert list(fig.layout.yaxis.tickvals) == []

    def test_pace_bars_use_wds_accent_amber(self):
        # Regression guard: the monthly-pace bars render in the WDS --accent amber (#e0a63c),
        # deliberately distinct from the --primary teal used by the buttons/chips/nav.
        fig = _pace_figure([MonthPoint(month="2026-06", total=Decimal("5000"))])
        assert fig.data[0].marker.color == "#e0a63c"

    def test_pace_bars_are_slim(self):
        # The bars are deliberately narrow (high bargap) so the chart supports the hero
        # figure rather than shouting (UX-DR1).
        fig = _pace_figure([MonthPoint(month="2026-06", total=Decimal("5000"))])
        assert fig.layout.bargap == 0.6


# ---------------------------------------------------------------------------
# Simple handlers
# ---------------------------------------------------------------------------

class TestSimpleHandlers:
    def test_toggle_why_and_drillin(self, make_state):
        s = make_state(DashboardState)
        s.toggle_why()
        s.toggle_drillin()
        assert s.why_open is True and s.drillin_open is True

    def test_navigation_handlers_redirect(self, make_state):
        s = make_state(DashboardState)
        assert s.go_commitments() is not None
        assert s.go_upload() is not None


# ---------------------------------------------------------------------------
# _apply_evidence — every display branch, via constructed engine-shaped inputs
# ---------------------------------------------------------------------------

def _evidence(**overrides):
    base = dict(
        safe_to_spend_today=Decimal("1500"),
        safe_to_spend_after_income=Decimal("8000"),
        safety_ok=True,
        buffer_intact=True,
        data_quality_flags=[],
        prediction_confidence="High",
        drivers=["Rent is your biggest bill."],
        reserved_total=Decimal("20000"),
        days_to_income=10,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def _data(evidence, **overrides):
    base = dict(
        evidence=evidence,
        has_data=True,
        statement_end_date=__import__("datetime").date(2026, 6, 30),
        next_income_date=__import__("datetime").date(2026, 7, 1),
        is_stale=False,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


class TestApplyEvidence:
    def test_income_known_populates_after_income_row(self, make_state):
        s = make_state(DashboardState)
        s._apply_evidence(_data(_evidence()), score=80)
        assert s.has_income is True
        assert s.after_income_amount and "salary" in s.after_income_label.lower()
        assert s.why_text == "Rent is your biggest bill."

    def test_income_amount_unknown_prompts_for_amount(self, make_state):
        s = make_state(DashboardState)
        ev = _evidence(safe_to_spend_after_income=None, data_quality_flags=["income_amount_unknown"])
        s._apply_evidence(_data(ev), score=50)
        assert s.has_income is False
        assert "how much" in s.after_income_label

    def test_no_income_detected_uses_approved_copy(self, make_state):
        s = make_state(DashboardState)
        ev = _evidence(safe_to_spend_after_income=None)
        s._apply_evidence(_data(ev, next_income_date=None), score=50)
        assert s.has_income is False
        assert "payday" in s.after_income_label.lower()

    def test_shortfall_and_buffer_flags(self, make_state):
        s = make_state(DashboardState)
        s._apply_evidence(_data(_evidence(safety_ok=False)), score=20)
        assert s.shortfall is True
        s._apply_evidence(_data(_evidence(safety_ok=True, buffer_intact=False)), score=40)
        assert s.buffer_dented is True

    def test_no_drivers_falls_back_to_honest_copy(self, make_state):
        s = make_state(DashboardState)
        s._apply_evidence(_data(_evidence(drivers=[])), score=60)
        assert s.why_text == WHY_FALLBACK

    def test_no_statement_end_date_leaves_caveat_blank(self, make_state):
        s = make_state(DashboardState)
        s._apply_evidence(_data(_evidence(), statement_end_date=None), score=60)
        assert s.freshness_caveat == ""


# ---------------------------------------------------------------------------
# _apply_score_events / _apply_timeline / _briefing_context
# ---------------------------------------------------------------------------

class TestApplyHelpers:
    def test_apply_score_events_signs_delta(self, make_state):
        s = make_state(DashboardState)
        events = [SimpleNamespace(delta=4, explanation="up", timestamp=__import__("datetime").datetime(2026, 6, 1))]
        s._apply_score_events(events)
        assert s.score_events[0].delta == "+4" and s.score_events[0].explanation == "up"

    def test_apply_timeline_sorts_by_due(self, make_state):
        import datetime

        s = make_state(DashboardState)
        commitments = [
            SimpleNamespace(due_day=25, name="Rent", amount=Decimal("15000"), criticality="critical"),
            SimpleNamespace(due_day=5, name="Netflix", amount=Decimal("500"), criticality="flexible"),
        ]
        s._apply_timeline(commitments, as_of=datetime.date(2026, 6, 1))
        assert [t.name for t in s.timeline] == ["Netflix", "Rent"]
        assert s.timeline[0].tier == "Flexible"

    def test_apply_timeline_defaults_anchor_to_today(self, make_state):
        s = make_state(DashboardState)
        s._apply_timeline([], as_of=None)
        assert s.timeline == []

    def test_briefing_context_preformats_money(self, make_state):
        s = make_state(DashboardState)
        ctx = s._briefing_context(_data(_evidence()))
        assert ctx.safe_to_spend_today.startswith("₹")
        # None after-income stays None (never a fabricated ₹0).
        ctx2 = s._briefing_context(_data(_evidence(safe_to_spend_after_income=None), next_income_date=None))
        assert ctx2.safe_to_spend_after_income is None and ctx2.next_income_date is None


# ---------------------------------------------------------------------------
# load_dashboard — async, over seeded data
# ---------------------------------------------------------------------------

def _seed_txns(session, user_id):
    rows = [
        Transaction(user_id=user_id, date="2026-06-01", description_raw="SWIGGY",
                    amount=Decimal("450"), direction="debit", category="Food & Dining",
                    category_source="rule", category_confidence=1.0),
        Transaction(user_id=user_id, date="2026-06-03", description_raw="RENT",
                    amount=Decimal("15000"), direction="debit", category="Rent",
                    category_source="rule", category_confidence=1.0),
        Transaction(user_id=user_id, date="2026-06-30", description_raw="SALARY ACME",
                    amount=Decimal("85000"), direction="credit", category="Salary",
                    category_source="rule", category_confidence=1.0),
    ]
    for r in rows:
        session.add(r)
    session.commit()


class TestLoadDashboard:
    def test_no_user_redirects_to_login(self, make_state):
        s = make_state(DashboardState, auth_token="no-session")
        events = drive(s.load_dashboard())
        assert any(e is not None for e in events)  # redirect yielded

    def test_empty_data_shows_empty_hero(self, make_state, seed_auth):
        _uid, token = seed_auth()  # a user with zero transactions
        s = make_state(DashboardState, auth_token=token)
        drive(s.load_dashboard())
        assert s.loaded is True and s.has_data is False
        assert s.why_text == EMPTY_HERO_COPY

    def test_happy_path_loads_figures_and_briefing(self, make_state, seed_auth, db_session, monkeypatch):
        monkeypatch.setattr(dash_mod, "generate_briefing", lambda ctx: "Here's your briefing.")
        uid, token = seed_auth()
        _seed_txns(db_session, uid)
        s = make_state(DashboardState, auth_token=token)
        drive(s.load_dashboard())
        assert s.loaded is True and s.has_data is True
        assert s.safe_to_spend_today.startswith("₹")
        assert s.briefing == "Here's your briefing." and s.briefing_loading is False
