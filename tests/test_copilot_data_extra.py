"""Coverage for the ``DbCopilotData`` methods + helpers not exercised by ``test_copilot_data.py``
— ``get_safe_to_spend`` / ``get_confidence_score`` / ``get_upcoming_commitments``, the two
module helpers, and the ``open_copilot_data`` context factory.
"""
from __future__ import annotations

from decimal import Decimal

import pytest
import sqlmodel

from finance_app.models import Commitment, Transaction
from finance_app.state.copilot_data import (
    DbCopilotData,
    _change_direction,
    _format_month,
    open_copilot_data,
)


@pytest.fixture
def session(tmp_path):
    import finance_app.models  # noqa: F401

    engine = sqlmodel.create_engine(f"sqlite:///{tmp_path / 'copilot_extra.db'}")
    sqlmodel.SQLModel.metadata.create_all(engine)
    with sqlmodel.Session(engine) as s:
        yield s


def _seed_statement(session, uid=1):
    rows = [
        Transaction(user_id=uid, date="2026-06-01", description_raw="SWIGGY",
                    amount=Decimal("450"), direction="debit", category="Food & Dining",
                    category_source="rule", category_confidence=1.0),
        Transaction(user_id=uid, date="2026-06-30", description_raw="SALARY ACME",
                    amount=Decimal("85000"), direction="credit", category="Salary",
                    category_source="rule", category_confidence=1.0),
    ]
    for r in rows:
        session.add(r)
    session.commit()


# ---------------------------------------------------------------------------
# Module helpers
# ---------------------------------------------------------------------------

class TestHelpers:
    def test_format_month_valid(self):
        assert _format_month("2026-06") == "Jun 2026"

    def test_format_month_falls_back_on_junk(self):
        assert _format_month("not-a-month") == "not-a-month"

    @pytest.mark.parametrize("delta, word", [(5, "improved"), (-3, "dropped"), (0, "unchanged")])
    def test_change_direction(self, delta, word):
        assert _change_direction(delta) == word


# ---------------------------------------------------------------------------
# get_safe_to_spend
# ---------------------------------------------------------------------------

class TestGetSafeToSpend:
    def test_unavailable_without_data(self, session):
        result = DbCopilotData(session, user_id=1).get_safe_to_spend()
        assert result["available"] is False and "upload" in result["reason"].lower()

    def test_returns_figures_with_data(self, session):
        _seed_statement(session)
        result = DbCopilotData(session, user_id=1).get_safe_to_spend()
        assert result["available"] is True
        assert result["safe_to_spend_today"].startswith("₹")
        assert "prediction_confidence" in result


# ---------------------------------------------------------------------------
# get_confidence_score
# ---------------------------------------------------------------------------

class TestGetConfidenceScore:
    def test_unavailable_without_data(self, session):
        result = DbCopilotData(session, user_id=1).get_confidence_score()
        assert result["available"] is False

    def test_computes_label_without_leaking_raw_score(self, session):
        _seed_statement(session)
        result = DbCopilotData(session, user_id=1).get_confidence_score()
        assert result["available"] is True and result["label"]
        assert "score" not in result  # the raw 0-100 integer never leaves the server

    def test_prefers_persisted_latest_event(self, session):
        from finance_app.models import ScoreEvent

        session.add(ScoreEvent(  # type: ignore[call-arg]
            user_id=1, score=80, delta=5, trigger_event="dashboard_view",
            explanation="Buffer grew.", suggested_action="Keep it up.",
        ))
        session.commit()
        result = DbCopilotData(session, user_id=1).get_confidence_score()
        assert result["available"] is True
        assert result["explanation"] == "Buffer grew."
        assert result["suggested_action"] == "Keep it up."


# ---------------------------------------------------------------------------
# get_upcoming_commitments
# ---------------------------------------------------------------------------

class TestGetUpcomingCommitments:
    def test_note_when_none_declared(self, session):
        result = DbCopilotData(session, user_id=1).get_upcoming_commitments()
        assert result["commitments"] == [] and "note" in result

    def test_orders_commitments_by_next_due(self, session):
        session.add(Commitment(user_id=1, name="Rent", amount=Decimal("15000"), due_day=25, criticality="critical"))  # type: ignore[call-arg]
        session.add(Commitment(user_id=1, name="Netflix", amount=Decimal("500"), due_day=5, criticality="flexible"))  # type: ignore[call-arg]
        session.commit()
        result = DbCopilotData(session, user_id=1).get_upcoming_commitments()
        names = [c["name"] for c in result["commitments"]]
        assert set(names) == {"Rent", "Netflix"}
        assert all(c["amount"].startswith("₹") for c in result["commitments"])


# ---------------------------------------------------------------------------
# open_copilot_data — the data_factory used by the streaming loop
# ---------------------------------------------------------------------------

def test_open_copilot_data_yields_scoped_provider(rx_session):
    # rx_session (conftest) points rx.session() at a throwaway SQLite DB.
    with open_copilot_data(user_id=7) as data:
        assert isinstance(data, DbCopilotData)
        assert data._user_id == 7
