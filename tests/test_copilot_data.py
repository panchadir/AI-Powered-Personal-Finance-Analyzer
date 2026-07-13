"""Regression tests for ``DbCopilotData``'s real DB queries (finance_app/state/copilot_data.py).

This is the concrete provider behind the Copilot's read-only tools (``services/narrate/tools.py``
only defines the ``CopilotData`` Protocol + dispatcher, and is tested against a fake provider in
``tests/narrate/test_copilot_tools.py``). No test previously exercised this module's actual query
behavior — this locks in the ``user_id`` scoping (AD-4 / IDOR guard) the Copilot tools depend on
for `query_transactions` and `get_spending_by_category`.
"""
from __future__ import annotations

from decimal import Decimal

import pytest
import sqlmodel

from finance_app.models import Insight, ScoreEvent, Transaction, UploadedFile
from finance_app.state.copilot_data import DbCopilotData


@pytest.fixture
def session(tmp_path):
    engine = sqlmodel.create_engine(f"sqlite:///{tmp_path / 'copilot_data.db'}")
    sqlmodel.SQLModel.metadata.create_all(engine)
    with sqlmodel.Session(engine) as s:
        yield s


def _add_txn(session, **overrides) -> None:
    defaults = dict(
        user_id=1,
        date="2026-06-15",
        description_raw="SWIGGY",
        merchant_normalized="Swiggy",
        amount=Decimal("250.00"),
        direction="debit",
        category="Dining",
    )
    defaults.update(overrides)
    session.add(Transaction(**defaults))  # type: ignore[call-arg]
    session.commit()


def _add_insight(session, **overrides) -> None:
    defaults = dict(
        user_id=1,
        pattern_name="dining_creep",
        observation="Your dining spend is climbing.",
        evidence="₹4,200 this month vs ₹2,800 last month.",
        explanation="That's a 50% increase month over month.",
        effect="At this pace you'll overshoot your usual budget.",
        action_suggestion="Consider capping weekend dining.",
        status="active",
        severity="important",
        dedup_key="dining_creep",
    )
    defaults.update(overrides)
    session.add(Insight(**defaults))  # type: ignore[call-arg]
    session.commit()


def _add_score_event(session, **overrides) -> None:
    defaults = dict(
        user_id=1,
        score=75,
        delta=10,
        trigger_event="statement_upload",
        explanation="Your buffer grew after the latest statement.",
        suggested_action="Keep it up.",
    )
    defaults.update(overrides)
    session.add(ScoreEvent(**defaults))  # type: ignore[call-arg]
    session.commit()


class TestQueryTransactions:
    def test_returns_only_the_requesting_users_rows(self, session):
        _add_txn(session, user_id=1, amount=Decimal("100"))
        _add_txn(session, user_id=2, amount=Decimal("999"))  # another user's row
        data = DbCopilotData(session, user_id=1)

        result = data.query_transactions(category=None, direction=None, limit=None)
        assert result["count"] == 1
        assert result["transactions"][0]["amount"] == "₹100"

    def test_filters_by_category_and_direction(self, session):
        _add_txn(session, category="Dining", direction="debit", amount=Decimal("300"))
        _add_txn(session, category="Groceries", direction="debit", amount=Decimal("500"))
        _add_txn(session, category="Dining", direction="credit", amount=Decimal("50"))
        data = DbCopilotData(session, user_id=1)

        result = data.query_transactions(category="Dining", direction="debit", limit=None)
        assert result["count"] == 1
        assert result["transactions"][0]["amount"] == "₹300"

    def test_respects_the_limit_cap_at_fifty(self, session):
        for i in range(60):
            _add_txn(session, date=f"2026-06-{(i % 28) + 1:02d}", amount=Decimal("10"))
        data = DbCopilotData(session, user_id=1)

        result = data.query_transactions(category=None, direction=None, limit=999)
        assert result["count"] == 50


class TestGetSpendingByCategory:
    def test_sums_debits_grouped_by_category_excluding_credits(self, session):
        _add_txn(session, category="Dining", direction="debit", amount=Decimal("300"))
        _add_txn(session, category="Dining", direction="debit", amount=Decimal("200"))
        _add_txn(session, category="Groceries", direction="debit", amount=Decimal("500"))
        _add_txn(session, category="Dining", direction="credit", amount=Decimal("9999"))
        data = DbCopilotData(session, user_id=1)

        result = data.get_spending_by_category()
        by_category = {row["category"]: row["total"] for row in result["by_category"]}
        assert by_category["Dining"] == "₹500"
        assert by_category["Groceries"] == "₹500"

    def test_scopes_to_the_requesting_user_only(self, session):
        _add_txn(session, user_id=1, category="Dining", amount=Decimal("100"))
        _add_txn(session, user_id=2, category="Dining", amount=Decimal("99999"))
        data = DbCopilotData(session, user_id=1)

        result = data.get_spending_by_category()
        assert result["by_category"] == [{"category": "Dining", "total": "₹100"}]

    def test_reports_unavailable_when_no_categorised_spending_exists(self, session):
        data = DbCopilotData(session, user_id=1)
        result = data.get_spending_by_category()
        assert result["available"] is False


class TestGetSpendingTrend:
    def test_groups_debits_by_month_oldest_first(self, session):
        _add_txn(session, date="2026-05-10", amount=Decimal("100"))
        _add_txn(session, date="2026-06-10", amount=Decimal("300"))
        _add_txn(session, date="2026-06-20", amount=Decimal("200"))
        data = DbCopilotData(session, user_id=1)

        result = data.get_spending_trend(category=None)
        assert result["by_month"] == [
            {"month": "May 2026", "total": "₹100"},
            {"month": "Jun 2026", "total": "₹500"},
        ]

    def test_scopes_to_a_single_category_when_given(self, session):
        _add_txn(session, date="2026-06-01", category="Dining", amount=Decimal("300"))
        _add_txn(session, date="2026-06-02", category="Groceries", amount=Decimal("900"))
        data = DbCopilotData(session, user_id=1)

        result = data.get_spending_trend(category="Dining")
        assert result["category"] == "Dining"
        assert result["by_month"] == [{"month": "Jun 2026", "total": "₹300"}]

    def test_scopes_to_the_requesting_user_only(self, session):
        _add_txn(session, user_id=1, date="2026-06-01", amount=Decimal("100"))
        _add_txn(session, user_id=2, date="2026-06-01", amount=Decimal("99999"))
        data = DbCopilotData(session, user_id=1)

        result = data.get_spending_trend(category=None)
        assert result["by_month"] == [{"month": "Jun 2026", "total": "₹100"}]

    def test_unavailable_when_no_spend_for_category(self, session):
        _add_txn(session, category="Dining", amount=Decimal("100"))
        data = DbCopilotData(session, user_id=1)

        result = data.get_spending_trend(category="Travel")
        assert result["available"] is False


class TestGetInsights:
    def test_returns_active_insights_most_urgent_first(self, session):
        _add_insight(session, severity="flexible", dedup_key="a", observation="minor")
        _add_insight(session, severity="critical", dedup_key="b", observation="urgent")
        _add_insight(session, severity="important", dedup_key="c", observation="mid")
        data = DbCopilotData(session, user_id=1)

        result = data.get_insights()
        assert [i["observation"] for i in result["insights"]] == ["urgent", "mid", "minor"]
        assert result["insights"][0]["suggested_action"]  # action_suggestion mapped through

    def test_excludes_dismissed_insights(self, session):
        _add_insight(session, status="active", dedup_key="a", observation="shown")
        _add_insight(session, status="dismissed", dedup_key="b", observation="hidden")
        data = DbCopilotData(session, user_id=1)

        result = data.get_insights()
        assert [i["observation"] for i in result["insights"]] == ["shown"]

    def test_scopes_to_the_requesting_user_only(self, session):
        _add_insight(session, user_id=1, dedup_key="a", observation="mine")
        _add_insight(session, user_id=2, dedup_key="b", observation="theirs")
        data = DbCopilotData(session, user_id=1)

        result = data.get_insights()
        assert [i["observation"] for i in result["insights"]] == ["mine"]

    def test_empty_note_when_no_active_insights(self, session):
        data = DbCopilotData(session, user_id=1)
        result = data.get_insights()
        assert result["insights"] == []
        assert "note" in result


class TestGetScoreHistory:
    def test_returns_labels_and_change_direction_never_raw_score(self, session):
        _add_score_event(session, score=75, delta=10)
        data = DbCopilotData(session, user_id=1)

        result = data.get_score_history(limit=None)
        entry = result["history"][0]
        assert entry["label"] == "Well prepared"
        assert entry["change"] == "improved"
        # The raw 0-100 score and numeric delta must never leak (FR-5.5).
        assert "score" not in entry and "delta" not in entry
        assert "75" not in str(entry)

    def test_newest_first_and_direction_reflects_delta_sign(self, session):
        _add_score_event(session, score=75, delta=10)   # older
        _add_score_event(session, score=45, delta=-30)  # newer
        data = DbCopilotData(session, user_id=1)

        result = data.get_score_history(limit=None)
        assert [e["change"] for e in result["history"]] == ["dropped", "improved"]
        assert result["history"][0]["label"] == "On track"

    def test_respects_the_limit_cap_at_twenty(self, session):
        for i in range(25):
            _add_score_event(session, score=50 + i, delta=1)
        data = DbCopilotData(session, user_id=1)

        result = data.get_score_history(limit=999)
        assert len(result["history"]) == 20

    def test_scopes_to_the_requesting_user_only(self, session):
        _add_score_event(session, user_id=1, explanation="mine")
        _add_score_event(session, user_id=2, explanation="theirs")
        data = DbCopilotData(session, user_id=1)

        result = data.get_score_history(limit=None)
        assert [e["explanation"] for e in result["history"]] == ["mine"]

    def test_unavailable_when_no_history(self, session):
        data = DbCopilotData(session, user_id=1)
        result = data.get_score_history(limit=None)
        assert result["available"] is False


class TestGetDetectedSubscriptions:
    def test_returns_unconfirmed_recurring_charges(self, session):
        # Two monthly Netflix debits ~31 days apart, same amount → a detected candidate.
        _add_txn(session, date="2026-05-05", merchant_normalized="Netflix", amount=Decimal("500"))
        _add_txn(session, date="2026-06-05", merchant_normalized="Netflix", amount=Decimal("500"))
        data = DbCopilotData(session, user_id=1)

        result = data.get_detected_subscriptions()
        subs = result["detected_subscriptions"]
        assert len(subs) == 1
        assert "netflix" in subs[0]["merchant"].lower()
        assert subs[0]["amount"] == "₹500"
        assert subs[0]["times_seen"] == 2

    def test_empty_note_when_nothing_recurring(self, session):
        _add_txn(session, amount=Decimal("100"))  # a single charge is not a cadence
        data = DbCopilotData(session, user_id=1)

        result = data.get_detected_subscriptions()
        assert result["detected_subscriptions"] == []
        assert "note" in result

    def test_scopes_to_the_requesting_user_only(self, session):
        for d in ("2026-05-05", "2026-06-05"):
            _add_txn(session, user_id=2, date=d, merchant_normalized="Netflix", amount=Decimal("500"))
        data = DbCopilotData(session, user_id=1)

        assert data.get_detected_subscriptions()["detected_subscriptions"] == []


class TestGetIncomeSummary:
    def test_detects_salary_and_returns_amount_date_confidence(self, session):
        _add_txn(
            session,
            date="2026-06-01",
            description_raw="ACME PAYROLL SALARY CREDIT",
            amount=Decimal("50000"),
            direction="credit",
        )
        data = DbCopilotData(session, user_id=1)

        result = data.get_income_summary()
        assert result["available"] is True
        assert result["expected_amount"] == "₹50,000"
        assert result["detection_confidence"] in {"Low", "Medium", "High"}
        assert result["next_income_date"]  # a projected date, non-empty

    def test_unavailable_when_no_salary_shaped_credit(self, session):
        _add_txn(session, amount=Decimal("500"))  # a plain debit, no salary
        data = DbCopilotData(session, user_id=1)

        assert data.get_income_summary()["available"] is False

    def test_unavailable_when_no_data(self, session):
        data = DbCopilotData(session, user_id=1)
        assert data.get_income_summary()["available"] is False


class TestGetDataCoverage:
    def test_reports_counts_range_and_freshness_flag(self, session):
        _add_txn(session, date="2026-06-01", amount=Decimal("100"))
        _add_txn(session, date="2026-06-20", amount=Decimal("200"))
        session.add(UploadedFile(user_id=1, filename="june.pdf"))  # type: ignore[call-arg]
        session.commit()
        data = DbCopilotData(session, user_id=1)

        result = data.get_data_coverage()
        assert result["available"] is True
        assert result["statements_uploaded"] == 1
        assert result["transaction_count"] == 2
        assert result["earliest_transaction"] and result["latest_transaction"]
        assert result["earliest_transaction"] != result["latest_transaction"]
        assert isinstance(result["is_stale"], bool)

    def test_flags_clearly_old_data_as_stale(self, session):
        _add_txn(session, date="2020-01-01", amount=Decimal("100"))
        data = DbCopilotData(session, user_id=1)

        result = data.get_data_coverage()
        assert result["is_stale"] is True
        assert "note" in result

    def test_unavailable_when_no_data(self, session):
        data = DbCopilotData(session, user_id=1)
        assert data.get_data_coverage()["available"] is False
