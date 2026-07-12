"""Tests for the DB<->detectors<->narrator bridge (Story 7.3, finance_app/state/insights_bridge.py).

Session-injected against in-memory SQLite, so no Reflex app is needed. No LLM calls: the
`ANTHROPIC_API_KEY` env var is unset (autouse fixture), so `generate_insight_narration`
naturally takes its documented, deterministic, zero-network fallback path (Story 7.2).

What is asserted here is the wiring Story 7.1/7.2 don't cover: the resurface/dedup state
machine (never duplicate an unchanged active row, update it in place when it changes
materially, only ever create a new row from the dismissed-and-changed or never-seen path,
never un-dismiss an old row), the multi-instance dedup key for Zombie subscriptions, and the
`user_id` scoping on dismiss (AD-4 / IDOR guard).
"""
from __future__ import annotations

import datetime
from decimal import Decimal

import pytest
import sqlmodel

import finance_app.models  # noqa: F401 — registers all app tables
from finance_app.models import Insight, Transaction
from finance_app.state.insights_bridge import (
    _headline_metric,
    _materially_changed,
    dismiss_insight,
    refresh_insights,
    top_active_insight,
)
from reflex_local_auth.user import LocalUser
from services.narrate.config import API_KEY_ENV_VAR


@pytest.fixture
def session(tmp_path):
    engine = sqlmodel.create_engine(f"sqlite:///{tmp_path / 'insights_bridge.db'}")
    sqlmodel.SQLModel.metadata.create_all(engine)
    with sqlmodel.Session(engine) as s:
        yield s


@pytest.fixture(autouse=True)
def _no_api_key(monkeypatch):
    """No test may reach the real API, even by accident (mirrors test_insight_narrator.py)."""
    monkeypatch.delenv(API_KEY_ENV_VAR, raising=False)


def make_user(session, email: str) -> LocalUser:
    user = LocalUser(  # type: ignore[call-arg]
        username=email, password_hash=LocalUser.hash_password("supersecret8"), enabled=True
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def add_txn(session, user_id, date, description, amount, *, direction="debit", merchant=None):
    session.add(
        Transaction(  # type: ignore[call-arg]
            user_id=user_id,
            date=date,
            description_raw=description,
            merchant_normalized=merchant,
            amount=Decimal(amount),
            direction=direction,
        )
    )
    session.commit()


def _add_small_purchases(session, user_id: int, count: int, amount: str, start_day: int = 1):
    for i in range(count):
        add_txn(session, user_id, f"2026-06-{start_day + i:02d}", f"Coffee {i}", amount)


def _active_by_key(active: list[Insight], dedup_key: str) -> Insight | None:
    return next((row for row in active if row.dedup_key == dedup_key), None)


class TestHeadlineMetricAndMateriallyChanged:
    def test_known_pattern_reads_its_headline_metric_key(self):
        assert _headline_metric(
            "Death by small purchases", {"total": Decimal("2400")}
        ) == Decimal("2400")

    def test_unrecognized_pattern_returns_none(self):
        assert _headline_metric("Some future pattern", {"anything": Decimal("1")}) is None

    def test_unrecognized_or_missing_value_is_always_treated_as_changed(self):
        assert _materially_changed(None, Decimal("100")) is True
        assert _materially_changed(Decimal("100"), None) is True

    def test_zero_old_value_guard(self):
        assert _materially_changed(Decimal("0"), Decimal("0")) is False
        assert _materially_changed(Decimal("50"), Decimal("0")) is True

    def test_threshold_boundary(self):
        # 2400 -> 2760 is exactly +15%
        assert _materially_changed(Decimal("2760"), Decimal("2400")) is True
        assert _materially_changed(Decimal("2759"), Decimal("2400")) is False


class TestRefreshInsightsPersistence:
    def test_persists_a_new_active_row_for_a_fresh_user(self, session):
        user = make_user(session, "a@example.com")
        _add_small_purchases(session, user.id, count=8, amount="300")  # total 2400

        data = refresh_insights(session, user.id)
        row = _active_by_key(data.active, "Death by small purchases")
        assert row is not None
        assert row.observation and row.explanation and row.effect and row.action_suggestion
        assert row.metric_value == Decimal("2400")
        assert row.severity in ("critical", "important", "flexible")

    def test_does_not_duplicate_an_unchanged_active_pattern(self, session):
        user = make_user(session, "b@example.com")
        _add_small_purchases(session, user.id, count=8, amount="300")

        first = refresh_insights(session, user.id)
        row_id = _active_by_key(first.active, "Death by small purchases").id

        second = refresh_insights(session, user.id)  # no new data — same total
        matching = [r for r in second.active if r.dedup_key == "Death by small purchases"]
        assert len(matching) == 1
        assert matching[0].id == row_id  # same row, not a duplicate

    def test_updates_the_active_row_in_place_when_metric_changes_materially(self, session):
        user = make_user(session, "c@example.com")
        _add_small_purchases(session, user.id, count=8, amount="300")  # total 2400
        first = refresh_insights(session, user.id)
        original_id = _active_by_key(first.active, "Death by small purchases").id

        # Two more small purchases push the total to 3000 (+25%, well over the 15% bar).
        _add_small_purchases(session, user.id, count=2, amount="300", start_day=20)
        second = refresh_insights(session, user.id)
        matching = [r for r in second.active if r.dedup_key == "Death by small purchases"]

        assert len(matching) == 1  # updated in place, not duplicated
        assert matching[0].id == original_id
        assert matching[0].metric_value == Decimal("3000")

    def test_dismissed_pattern_does_not_resurface_when_unchanged(self, session):
        user = make_user(session, "d@example.com")
        _add_small_purchases(session, user.id, count=8, amount="300")
        first = refresh_insights(session, user.id)
        row = _active_by_key(first.active, "Death by small purchases")
        dismiss_insight(session, user.id, row.id)

        second = refresh_insights(session, user.id)  # same data, still dismissed
        assert _active_by_key(second.active, "Death by small purchases") is None

        dismissed = session.get(Insight, row.id)
        assert dismissed.status == "dismissed"

    def test_dismissed_pattern_resurfaces_as_a_new_row_when_materially_changed(self, session):
        user = make_user(session, "e@example.com")
        _add_small_purchases(session, user.id, count=8, amount="300")  # total 2400
        first = refresh_insights(session, user.id)
        old_row = _active_by_key(first.active, "Death by small purchases")
        dismiss_insight(session, user.id, old_row.id)

        # Push the total up by >15%.
        _add_small_purchases(session, user.id, count=2, amount="300", start_day=20)  # -> 3000
        second = refresh_insights(session, user.id)
        new_row = _active_by_key(second.active, "Death by small purchases")

        assert new_row is not None
        assert new_row.id != old_row.id  # a brand-new row, never the un-dismissed old one
        still_dismissed = session.get(Insight, old_row.id)
        assert still_dismissed.status == "dismissed"  # old row is never un-dismissed

    def test_multiple_zombie_subscriptions_get_independent_dedup_keys(self, session):
        user = make_user(session, "f@example.com")
        add_txn(session, user.id, "2026-05-05", "NETFLIX", "499", merchant="Netflix")
        add_txn(session, user.id, "2026-06-04", "NETFLIX", "499", merchant="Netflix")
        add_txn(session, user.id, "2026-05-10", "SPOTIFY", "199", merchant="Spotify")
        add_txn(session, user.id, "2026-06-09", "SPOTIFY", "199", merchant="Spotify")

        data = refresh_insights(session, user.id)
        zombie_rows = [r for r in data.active if r.pattern_name == "Zombie subscriptions"]
        assert len(zombie_rows) == 2
        keys = {r.dedup_key for r in zombie_rows}
        assert keys == {"Zombie subscriptions::Netflix", "Zombie subscriptions::Spotify"}

        # Dismissing one must not affect the other.
        netflix_row = next(r for r in zombie_rows if "Netflix" in r.dedup_key)
        dismiss_insight(session, user.id, netflix_row.id)
        after = refresh_insights(session, user.id)
        remaining = [r for r in after.active if r.pattern_name == "Zombie subscriptions"]
        assert len(remaining) == 1
        assert "Spotify" in remaining[0].dedup_key

    def test_data_months_reflects_current_live_history(self, session):
        user = make_user(session, "g@example.com")
        add_txn(session, user.id, "2026-01-15", "X", "100")
        add_txn(session, user.id, "2026-06-10", "Y", "100")
        data = refresh_insights(session, user.id)
        assert data.data_months == 6

    def test_active_row_for_an_unmapped_pattern_is_not_needlessly_re_narrated(
        self, session, monkeypatch
    ):
        """A future/unrecognized pattern name has no headline-metric mapping, so its
        metric_value is always None. Without the both-None guard, an already-active row
        would be re-narrated (an LLM call) and its `created_at` bumped on every single
        page load forever, instead of being left alone like every other unchanged pattern."""
        from services.engine.insights import InsightCandidate

        user = make_user(session, "j@example.com")

        def fake_run_all_detectors(ctx):
            return [
                InsightCandidate(
                    pattern_name="Some future pattern",
                    severity="important",
                    evidence=(),
                    metrics={},
                    data_months=1,
                )
            ]

        monkeypatch.setattr(
            "finance_app.state.insights_bridge.run_all_detectors", fake_run_all_detectors
        )

        first = refresh_insights(session, user.id)
        row = _active_by_key(first.active, "Some future pattern")
        assert row is not None
        original_created_at = row.created_at

        second = refresh_insights(session, user.id)
        row_again = _active_by_key(second.active, "Some future pattern")
        assert row_again.id == row.id
        assert row_again.created_at == original_created_at  # never bumped -- not re-narrated

    def test_dismissed_insight_for_an_unmapped_pattern_stays_dismissed(
        self, session, monkeypatch
    ):
        """Mirrors the active-row test above, but for the dismissed-row branch: without
        the same both-None guard there, a dismissed insight for an unrecognized pattern
        would read as "changed" on every refresh (both sides None) and immediately
        resurface as a brand-new active row, silently overriding the user's dismiss."""
        from services.engine.insights import InsightCandidate

        user = make_user(session, "l@example.com")

        def fake_run_all_detectors(ctx):
            return [
                InsightCandidate(
                    pattern_name="Some future pattern",
                    severity="important",
                    evidence=(),
                    metrics={},
                    data_months=1,
                )
            ]

        monkeypatch.setattr(
            "finance_app.state.insights_bridge.run_all_detectors", fake_run_all_detectors
        )

        first = refresh_insights(session, user.id)
        row = _active_by_key(first.active, "Some future pattern")
        dismiss_insight(session, user.id, row.id)

        second = refresh_insights(session, user.id)  # same (unknown) metric, still dismissed
        assert _active_by_key(second.active, "Some future pattern") is None

        still_dismissed = session.get(Insight, row.id)
        assert still_dismissed.status == "dismissed"

    def test_ordering_is_severity_tiered_and_a_material_change_resorts_to_top_of_tier(
        self, session, monkeypatch
    ):
        """AC #3: newest-first within severity tier. Also verifies the reason
        `_load_active` sorts by `created_at` (not `id`): an in-place update bumps
        `created_at`, which must move a materially-changed insight back to the top of
        its severity tier."""
        from services.engine.insights import InsightCandidate

        user = make_user(session, "m@example.com")

        def fake_detectors(ctx):
            return [
                InsightCandidate(
                    pattern_name="Post-payday spike",
                    severity="critical",
                    evidence=(),
                    metrics={"spike_pct": Decimal("50")},
                    data_months=6,
                ),
                InsightCandidate(
                    pattern_name="Death by small purchases",
                    severity="important",
                    evidence=(),
                    metrics={"total": Decimal("2400")},
                    data_months=6,
                ),
            ]

        monkeypatch.setattr("finance_app.state.insights_bridge.run_all_detectors", fake_detectors)
        first = refresh_insights(session, user.id)
        assert [r.severity for r in first.active] == ["critical", "important"]

        death_row = _active_by_key(first.active, "Death by small purchases")
        # Force an artificially old timestamp so a later real-time bump is unambiguously
        # newer, regardless of the test clock's resolution.
        death_row.created_at = datetime.datetime(2020, 1, 1)
        session.add(death_row)
        session.commit()

        def fake_detectors_plus_weekend(ctx):
            return fake_detectors(ctx) + [
                InsightCandidate(
                    pattern_name="Weekend vs weekday pace",
                    severity="important",
                    evidence=(),
                    metrics={"ratio": Decimal("1.5")},
                    data_months=6,
                )
            ]

        monkeypatch.setattr(
            "finance_app.state.insights_bridge.run_all_detectors", fake_detectors_plus_weekend
        )
        second = refresh_insights(session, user.id)
        important_rows = [r for r in second.active if r.severity == "important"]
        assert important_rows[0].pattern_name == "Weekend vs weekday pace"
        assert important_rows[1].pattern_name == "Death by small purchases"

        def fake_detectors_death_changed(ctx):
            return [
                InsightCandidate(
                    pattern_name="Post-payday spike",
                    severity="critical",
                    evidence=(),
                    metrics={"spike_pct": Decimal("50")},
                    data_months=6,
                ),
                InsightCandidate(
                    pattern_name="Death by small purchases",
                    severity="important",
                    evidence=(),
                    metrics={"total": Decimal("3000")},  # +25% -- materially changed
                    data_months=6,
                ),
                InsightCandidate(
                    pattern_name="Weekend vs weekday pace",
                    severity="important",
                    evidence=(),
                    metrics={"ratio": Decimal("1.5")},  # unchanged
                    data_months=6,
                ),
            ]

        monkeypatch.setattr(
            "finance_app.state.insights_bridge.run_all_detectors", fake_detectors_death_changed
        )
        third = refresh_insights(session, user.id)
        important_rows_2 = [r for r in third.active if r.severity == "important"]
        assert important_rows_2[0].pattern_name == "Death by small purchases"
        assert important_rows_2[0].metric_value == Decimal("3000")


class TestDismissInsight:
    def test_sets_status_and_dismissed_at(self, session):
        user = make_user(session, "h@example.com")
        _add_small_purchases(session, user.id, count=8, amount="300")
        data = refresh_insights(session, user.id)
        row = _active_by_key(data.active, "Death by small purchases")

        dismiss_insight(session, user.id, row.id)

        refreshed = session.get(Insight, row.id)
        assert refreshed.status == "dismissed"
        assert refreshed.dismissed_at is not None

    def test_is_a_no_op_for_a_foreign_users_insight(self, session):
        owner = make_user(session, "owner@example.com")
        attacker = make_user(session, "attacker@example.com")
        _add_small_purchases(session, owner.id, count=8, amount="300")
        data = refresh_insights(session, owner.id)
        row = _active_by_key(data.active, "Death by small purchases")

        dismiss_insight(session, attacker.id, row.id)  # wrong user_id

        untouched = session.get(Insight, row.id)
        assert untouched.status == "active"
        assert untouched.dismissed_at is None

    def test_is_a_no_op_for_a_nonexistent_id(self, session):
        user = make_user(session, "i@example.com")
        dismiss_insight(session, user.id, 999999)  # must not raise


class TestTopActiveInsight:
    """Story 7.4's read-only Dashboard-teaser query. Must delegate to `_load_active`'s
    ordering (severity tier, then newest-first), never run detectors or narrate."""

    def test_returns_none_for_a_fresh_user_with_no_insights(self, session):
        user = make_user(session, "n@example.com")
        assert top_active_insight(session, user.id) is None

    def test_returns_the_only_active_insight(self, session):
        user = make_user(session, "o@example.com")
        _add_small_purchases(session, user.id, count=8, amount="300")
        data = refresh_insights(session, user.id)
        expected = _active_by_key(data.active, "Death by small purchases")

        top = top_active_insight(session, user.id)
        assert top is not None
        assert top.id == expected.id

    def test_returns_none_when_the_only_insight_is_dismissed(self, session):
        user = make_user(session, "p@example.com")
        _add_small_purchases(session, user.id, count=8, amount="300")
        data = refresh_insights(session, user.id)
        row = _active_by_key(data.active, "Death by small purchases")
        dismiss_insight(session, user.id, row.id)

        assert top_active_insight(session, user.id) is None

    def test_returns_the_highest_severity_tier_row_first(self, session, monkeypatch):
        """Mirrors the severity-tier ordering test for `_load_active` itself -- this test
        only needs to confirm `top_active_insight` delegates to it, not re-derive the
        ordering logic."""
        from services.engine.insights import InsightCandidate

        user = make_user(session, "q@example.com")

        def fake_detectors(ctx):
            return [
                InsightCandidate(
                    pattern_name="Zombie subscriptions",
                    severity="flexible",
                    evidence=(),
                    metrics={"monthly_amount": Decimal("199"), "merchant": "Spotify"},
                    data_months=6,
                ),
                InsightCandidate(
                    pattern_name="Post-payday spike",
                    severity="critical",
                    evidence=(),
                    metrics={"spike_pct": Decimal("50")},
                    data_months=6,
                ),
                InsightCandidate(
                    pattern_name="Death by small purchases",
                    severity="important",
                    evidence=(),
                    metrics={"total": Decimal("2400")},
                    data_months=6,
                ),
            ]

        monkeypatch.setattr("finance_app.state.insights_bridge.run_all_detectors", fake_detectors)
        refresh_insights(session, user.id)

        top = top_active_insight(session, user.id)
        assert top is not None
        assert top.pattern_name == "Post-payday spike"
        assert top.severity == "critical"
