"""Handler coverage for ``finance_app/state/insights_state.py``.

``_parse_evidence`` is covered by ``tests/test_insights_state.py``; this drives the computed
vars, ``toggle_dismissed``, the async ``load_insights`` (mocking ``refresh_insights`` so no
detector/LLM round-trip happens), the ``dismiss`` lifecycle, and ``_to_card`` mapping.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

import finance_app.state.insights_state as insights_mod
from finance_app.models import Insight
from finance_app.state.insights_state import DEFAULT_ICON, InsightCardView, InsightsState
from tests.conftest import drive


def _row(**overrides):
    base = dict(
        id=1,
        pattern_name="Post-payday spike",
        observation="You spent fast after payday.",
        evidence='[{"date": "2026-07-05", "merchant": "Swiggy", "amount": "450"}]',
        explanation="That's 40% in three days.",
        effect="Your buffer thins by month-end.",
        action_suggestion="Spread it out.",
        severity="critical",
        tone="watch",
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def _fake_feed(active=None, wins=None, dismissed=None, data_months=2, txn_count=100):
    return SimpleNamespace(
        active=active if active is not None else [_row()],
        wins=wins if wins is not None else [],
        dismissed=dismissed if dismissed is not None else [],
        data_months=data_months,
        txn_count=txn_count,
    )


# ---------------------------------------------------------------------------
# Computed vars + toggle
# ---------------------------------------------------------------------------

class TestComputedVars:
    def test_counts_and_has_anything(self, make_state):
        s = make_state(InsightsState)
        s.cards = [InsightCardView(id=1, severity="critical"), InsightCardView(id=2, severity="important")]
        s.win_cards = [InsightCardView(id=3)]
        s.dismissed_cards = [InsightCardView(id=4)]
        assert s.watch_count == 2
        assert s.win_count == 1
        assert s.dismissed_count == 1
        assert s.needs_attention_count == 1  # only the critical one
        assert s.has_anything is True

    def test_has_anything_false_when_both_bands_empty(self, make_state):
        s = make_state(InsightsState)
        assert s.has_anything is False

    def test_toggle_dismissed(self, make_state):
        s = make_state(InsightsState)
        s.toggle_dismissed()
        assert s.show_dismissed is True


# ---------------------------------------------------------------------------
# _to_card mapping
# ---------------------------------------------------------------------------

class TestToCard:
    def test_maps_row_to_card_with_icon_and_href(self):
        card = InsightsState._to_card(_row())
        assert card.pattern_name == "Post-payday spike" and card.icon == "💸"
        assert card.evidence == ["5 Jul 2026 · Swiggy · ₹450"]
        assert card.severity_label == "Needs attention"
        assert card.copilot_href.startswith("/copilot?insight=1&pre=")

    def test_unknown_pattern_gets_default_icon(self):
        card = InsightsState._to_card(_row(pattern_name="Some new pattern"))
        assert card.icon == DEFAULT_ICON


# ---------------------------------------------------------------------------
# load_insights (async)
# ---------------------------------------------------------------------------

class TestLoadInsights:
    def test_no_user_redirects(self, make_state):
        s = make_state(InsightsState, auth_token="nope")
        events = drive(s.load_insights())
        assert any(e is not None for e in events)

    def test_refresh_failure_sets_loaded_and_bails(self, make_state, seed_auth, monkeypatch):
        def _boom(session, user_id):
            raise RuntimeError("detector exploded")

        monkeypatch.setattr(insights_mod, "refresh_insights", _boom)
        _uid, token = seed_auth()
        s = make_state(InsightsState, auth_token=token)
        drive(s.load_insights())
        assert s.loaded is True and s.cards == []

    def test_happy_path_populates_bands(self, make_state, seed_auth, monkeypatch):
        monkeypatch.setattr(
            insights_mod, "refresh_insights",
            lambda session, user_id: _fake_feed(active=[_row(id=1)], wins=[_row(id=2, tone="win")]),
        )
        _uid, token = seed_auth()
        s = make_state(InsightsState, auth_token=token)
        drive(s.load_insights())
        assert s.loaded is True and s.has_data is True
        assert len(s.cards) == 1 and len(s.win_cards) == 1
        assert s.insufficient_data is False

    def test_insufficient_data_flagged_for_sparse_user(self, make_state, seed_auth, monkeypatch):
        monkeypatch.setattr(
            insights_mod, "refresh_insights",
            lambda session, user_id: _fake_feed(active=[], data_months=0, txn_count=1),
        )
        _uid, token = seed_auth()
        s = make_state(InsightsState, auth_token=token)
        drive(s.load_insights())
        assert s.insufficient_data is True and s.has_data is False

    def test_highlight_param_emits_scroll_script(self, make_state, seed_auth, monkeypatch):
        monkeypatch.setattr(
            insights_mod, "refresh_insights",
            lambda session, user_id: _fake_feed(active=[_row(id=7)]),
        )
        _uid, token = seed_auth()
        s = make_state(InsightsState, auth_token=token, params={"highlight": "7"})
        events = drive(s.load_insights())
        assert s.highlight_id == 7
        assert any(e is not None for e in events)  # rx.call_script yielded

    def test_malformed_highlight_param_is_ignored(self, make_state, seed_auth, monkeypatch):
        monkeypatch.setattr(insights_mod, "refresh_insights", lambda session, user_id: _fake_feed())
        _uid, token = seed_auth()
        s = make_state(InsightsState, auth_token=token, params={"highlight": "not-an-int"})
        drive(s.load_insights())
        assert s.highlight_id == 0


# ---------------------------------------------------------------------------
# dismiss lifecycle
# ---------------------------------------------------------------------------

class TestDismiss:
    def _seed_insight(self, db_session, uid, insight_id=1):
        row = Insight(  # type: ignore[call-arg]
            user_id=uid, pattern_name="Post-payday spike", observation="x",
            evidence="[]", explanation="x", effect="x", action_suggestion="x",
            status="active", severity="critical", dedup_key=f"k{insight_id}",
        )
        db_session.add(row)
        db_session.commit()
        db_session.refresh(row)
        return row.id

    def test_dismiss_moves_card_and_persists(self, make_state, seed_auth, db_session):
        uid, token = seed_auth()
        iid = self._seed_insight(db_session, uid)
        s = make_state(InsightsState, auth_token=token)
        s.cards = [InsightCardView(id=iid, pattern_name="Post-payday spike")]
        s.dismiss(iid)
        assert s.cards == [] and len(s.dismissed_cards) == 1
        db_session.expire_all()
        assert db_session.get(Insight, iid).status == "dismissed"

    def test_dismiss_sweeps_win_band_too(self, make_state, seed_auth, db_session):
        uid, token = seed_auth()
        iid = self._seed_insight(db_session, uid)
        s = make_state(InsightsState, auth_token=token)
        s.win_cards = [InsightCardView(id=iid, tone="win")]
        s.dismiss(iid)
        assert s.win_cards == [] and len(s.dismissed_cards) == 1

    def test_dismiss_no_user_redirects(self, make_state):
        s = make_state(InsightsState, auth_token="nope")
        s.cards = [InsightCardView(id=1)]
        assert s.dismiss(1) is not None
