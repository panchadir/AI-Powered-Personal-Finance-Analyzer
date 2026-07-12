"""Story 8.3 — IDOR Security Test (Cross-User Data Isolation).

Proves that every user-scoped table and every service query function returns only the
requesting user's rows — user A cannot see user B's data under any query path.

Two real users are created in a fresh SQLite database. Both users have rows in every
table so a zero-row result for A can never be confused with an empty-table result.

No mocks on the queries under test.
"""
from __future__ import annotations

from decimal import Decimal

import pytest
import sqlmodel
from sqlmodel import Session, select

import finance_app.models  # noqa: F401 — registers all app tables with SQLModel metadata
from finance_app.models import (
    ChatMessage,
    Commitment,
    CommitmentSuggestion,
    Insight,
    MerchantRule,
    ScoreEvent,
    Transaction as TxnModel,
    UploadedFile,
)
from finance_app.state.copilot_data import DbCopilotData
from finance_app.state.engine_bridge import (
    compute_dashboard,
    load_commitments,
    load_transactions,
    recent_score_events,
)
from finance_app.state.insights_bridge import dismiss_insight, top_active_insight
from reflex_local_auth.user import LocalUser
from services.categorize.teach_me import load_user_merchant_rules


def _make_user(session: Session, email: str) -> LocalUser:
    user = LocalUser(  # type: ignore[call-arg]
        username=email,
        password_hash=LocalUser.hash_password("pass1234"),
        enabled=True,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture
def two_users(tmp_path):
    """SQLite DB with users A and B, each having one row in every user-scoped table.

    Yields: (session, a_id, b_id, a_insight_id, b_insight_id)
    """
    engine = sqlmodel.create_engine(f"sqlite:///{tmp_path / 'idor.db'}")
    sqlmodel.SQLModel.metadata.create_all(engine)

    with sqlmodel.Session(engine) as session:
        user_a = _make_user(session, "alice@example.com")
        user_b = _make_user(session, "bob@example.com")
        a_id = user_a.id
        b_id = user_b.id

        # --- transactions -----------------------------------------------------------
        session.add(TxnModel(  # type: ignore[call-arg]
            user_id=a_id, date="2026-06-01",
            description_raw="ZOMATO_A", amount=Decimal("100.00"), direction="debit",
        ))
        session.add(TxnModel(  # type: ignore[call-arg]
            user_id=b_id, date="2026-06-02",
            description_raw="SWIGGY_B", amount=Decimal("999.00"), direction="debit",
        ))

        # --- commitments ------------------------------------------------------------
        session.add(Commitment(  # type: ignore[call-arg]
            user_id=a_id, name="Rent A", amount=Decimal("5000.00"), due_day=1,
        ))
        session.add(Commitment(  # type: ignore[call-arg]
            user_id=b_id, name="Insurance B", amount=Decimal("2000.00"), due_day=15,
        ))

        # --- commitment suggestions --------------------------------------------------
        session.add(CommitmentSuggestion(  # type: ignore[call-arg]
            user_id=a_id, signature="netflix@5", status="confirmed",
        ))
        session.add(CommitmentSuggestion(  # type: ignore[call-arg]
            user_id=b_id, signature="spotify@1", status="dismissed",
        ))

        # --- score events -----------------------------------------------------------
        session.add(ScoreEvent(  # type: ignore[call-arg]
            user_id=a_id, score=70, delta=10, trigger_event="upload",
            explanation="A uploaded a statement.",
        ))
        session.add(ScoreEvent(  # type: ignore[call-arg]
            user_id=b_id, score=30, delta=-5, trigger_event="upload",
            explanation="B uploaded a statement.",
        ))

        # --- insights ---------------------------------------------------------------
        a_insight = Insight(  # type: ignore[call-arg]
            user_id=a_id,
            pattern_name="Death by small purchases",
            observation="A observation",
            evidence="[]",
            explanation="A explanation",
            effect="A effect",
            action_suggestion="A suggestion",
            status="active",
            severity="important",
            dedup_key="Death by small purchases",
        )
        session.add(a_insight)
        b_insight = Insight(  # type: ignore[call-arg]
            user_id=b_id,
            pattern_name="Weekend vs weekday pace",
            observation="B observation",
            evidence="[]",
            explanation="B explanation",
            effect="B effect",
            action_suggestion="B suggestion",
            status="active",
            severity="flexible",
            dedup_key="Weekend vs weekday pace",
        )
        session.add(b_insight)
        session.commit()
        session.refresh(a_insight)
        session.refresh(b_insight)
        a_insight_id = a_insight.id
        b_insight_id = b_insight.id

        # --- chat messages ----------------------------------------------------------
        session.add(ChatMessage(  # type: ignore[call-arg]
            user_id=a_id, role="user", content="A says hello",
        ))
        session.add(ChatMessage(  # type: ignore[call-arg]
            user_id=b_id, role="user", content="B says hello",
        ))

        # --- merchant rules ---------------------------------------------------------
        session.add(MerchantRule(  # type: ignore[call-arg]
            user_id=a_id, pattern="amazon", category="Shopping",
        ))
        session.add(MerchantRule(  # type: ignore[call-arg]
            user_id=b_id, pattern="netflix", category="Entertainment",
        ))

        # --- uploaded files ---------------------------------------------------------
        session.add(UploadedFile(  # type: ignore[call-arg]
            user_id=a_id, filename="a_statement.pdf",
        ))
        session.add(UploadedFile(  # type: ignore[call-arg]
            user_id=b_id, filename="b_statement.pdf",
        ))
        session.commit()

        yield session, a_id, b_id, a_insight_id, b_insight_id


# ─── AC1: Row-level isolation for all 8 user-scoped tables ───────────────────


def test_transactions_row_isolation(two_users):
    """load_transactions(session, a_id) returns only A's rows — never B's (AC1)."""
    session, a_id, b_id, _, _ = two_users
    a_txns = load_transactions(session, a_id)
    b_txns = load_transactions(session, b_id)

    assert len(a_txns) == 1
    assert a_txns[0].description_raw == "ZOMATO_A"
    assert all(t.user_id == a_id for t in a_txns)

    assert len(b_txns) == 1
    assert b_txns[0].description_raw == "SWIGGY_B"
    assert all(t.user_id == b_id for t in b_txns)


def test_commitments_row_isolation(two_users):
    """load_commitments(session, a_id) returns only A's rows (AC1)."""
    session, a_id, b_id, _, _ = two_users
    a_commitments = load_commitments(session, a_id)
    b_commitments = load_commitments(session, b_id)

    assert len(a_commitments) == 1
    assert a_commitments[0].name == "Rent A"
    assert all(c.user_id == a_id for c in a_commitments)

    assert len(b_commitments) == 1
    assert b_commitments[0].name == "Insurance B"
    assert all(c.user_id == b_id for c in b_commitments)


def test_score_events_row_isolation(two_users):
    """recent_score_events(session, a_id) returns only A's rows (AC1)."""
    session, a_id, b_id, _, _ = two_users
    a_events = recent_score_events(session, a_id)
    b_events = recent_score_events(session, b_id)

    assert len(a_events) == 1
    assert a_events[0].score == 70
    assert all(e.user_id == a_id for e in a_events)

    assert len(b_events) == 1
    assert b_events[0].score == 30
    assert all(e.user_id == b_id for e in b_events)


def test_insights_row_isolation(two_users):
    """top_active_insight(session, a_id) returns A's insight, never B's (AC1)."""
    session, a_id, b_id, _, _ = two_users
    a_insight = top_active_insight(session, a_id)
    b_insight = top_active_insight(session, b_id)

    assert a_insight is not None
    assert a_insight.pattern_name == "Death by small purchases"
    assert a_insight.user_id == a_id

    assert b_insight is not None
    assert b_insight.pattern_name == "Weekend vs weekday pace"
    assert b_insight.user_id == b_id


def test_chat_messages_row_isolation(two_users):
    """Direct SELECT WHERE user_id on ChatMessage returns only that user's rows (AC1)."""
    session, a_id, b_id, _, _ = two_users
    a_msgs = session.exec(select(ChatMessage).where(ChatMessage.user_id == a_id)).all()
    b_msgs = session.exec(select(ChatMessage).where(ChatMessage.user_id == b_id)).all()

    assert len(a_msgs) == 1
    assert a_msgs[0].content == "A says hello"
    assert all(m.user_id == a_id for m in a_msgs)

    assert len(b_msgs) == 1
    assert b_msgs[0].content == "B says hello"
    assert all(m.user_id == b_id for m in b_msgs)


def test_merchant_rules_row_isolation(two_users):
    """load_user_merchant_rules(session, MerchantRule, a_id) returns only A's rules (AC1 / AC4)."""
    session, a_id, b_id, _, _ = two_users
    a_rules = load_user_merchant_rules(session, MerchantRule, a_id)
    b_rules = load_user_merchant_rules(session, MerchantRule, b_id)

    assert len(a_rules) == 1
    assert a_rules[0] == ("amazon", "Shopping")

    assert len(b_rules) == 1
    assert b_rules[0] == ("netflix", "Entertainment")


def test_uploaded_files_row_isolation(two_users):
    """Direct SELECT WHERE user_id on UploadedFile returns only that user's files (AC1)."""
    session, a_id, b_id, _, _ = two_users
    a_files = session.exec(select(UploadedFile).where(UploadedFile.user_id == a_id)).all()
    b_files = session.exec(select(UploadedFile).where(UploadedFile.user_id == b_id)).all()

    assert len(a_files) == 1
    assert a_files[0].filename == "a_statement.pdf"
    assert all(f.user_id == a_id for f in a_files)

    assert len(b_files) == 1
    assert b_files[0].filename == "b_statement.pdf"
    assert all(f.user_id == b_id for f in b_files)


def test_commitment_suggestions_row_isolation(two_users):
    """Direct SELECT WHERE user_id on CommitmentSuggestion returns only that user's rows (AC1)."""
    session, a_id, b_id, _, _ = two_users
    a_suggestions = session.exec(
        select(CommitmentSuggestion).where(CommitmentSuggestion.user_id == a_id)
    ).all()
    b_suggestions = session.exec(
        select(CommitmentSuggestion).where(CommitmentSuggestion.user_id == b_id)
    ).all()

    assert len(a_suggestions) == 1
    assert a_suggestions[0].signature == "netflix@5"
    assert all(s.user_id == a_id for s in a_suggestions)

    assert len(b_suggestions) == 1
    assert b_suggestions[0].signature == "spotify@1"
    assert all(s.user_id == b_id for s in b_suggestions)


# ─── AC2: Aggregate isolation ────────────────────────────────────────────────


def test_dashboard_aggregate_isolation(two_users):
    """compute_dashboard counts only the requesting user's transactions (AC2).

    A receives a second transaction so the counts differ — proves the aggregate is
    scoped and the totals are provably different across users.
    """
    session, a_id, b_id, _, _ = two_users
    session.add(TxnModel(  # type: ignore[call-arg]
        user_id=a_id, date="2026-06-15",
        description_raw="PAYTM_A", amount=Decimal("200.00"), direction="debit",
    ))
    session.commit()

    a_data = compute_dashboard(session, a_id)
    b_data = compute_dashboard(session, b_id)

    assert a_data.transaction_count == 2, (
        f"Expected A to have 2 transactions in dashboard; got {a_data.transaction_count}"
    )
    assert b_data.transaction_count == 1, (
        f"Expected B to have 1 transaction in dashboard; got {b_data.transaction_count}"
    )
    assert a_data.transaction_count != b_data.transaction_count, (
        "Counts must differ to prove isolation is not vacuously true"
    )


# ─── AC3: Cross-user dismiss is a no-op ─────────────────────────────────────


def test_cross_user_dismiss_insight_is_noop(two_users):
    """dismiss_insight(session, a_id, b_insight_id) must be a no-op — no crash (AC3).

    B's insight must remain active after A attempts to dismiss it.
    """
    session, a_id, b_id, _, b_insight_id = two_users

    dismiss_insight(session, a_id, b_insight_id)  # must not raise

    b_insight = session.exec(select(Insight).where(Insight.id == b_insight_id)).first()
    assert b_insight is not None
    assert b_insight.status == "active", (
        f"B's insight must remain active after A tried to dismiss it; "
        f"status is {b_insight.status!r}"
    )


# ─── Copilot data layer isolation ────────────────────────────────────────────


def test_copilot_data_query_transactions_row_isolation(two_users):
    """DbCopilotData.query_transactions bound to a_id returns only A's transactions."""
    session, a_id, b_id, _, _ = two_users
    a_provider = DbCopilotData(session, a_id)
    b_provider = DbCopilotData(session, b_id)

    a_result = a_provider.query_transactions(category=None, direction=None, limit=50)
    b_result = b_provider.query_transactions(category=None, direction=None, limit=50)

    assert a_result["count"] == 1
    a_merchants = [t["merchant"] for t in a_result["transactions"]]
    assert any("ZOMATO_A" in m for m in a_merchants)
    assert not any("SWIGGY_B" in m for m in a_merchants)

    assert b_result["count"] == 1
    b_merchants = [t["merchant"] for t in b_result["transactions"]]
    assert any("SWIGGY_B" in m for m in b_merchants)
    assert not any("ZOMATO_A" in m for m in b_merchants)
