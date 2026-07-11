"""Tests for the DB→engine bridge (Epic 5, finance_app/state/engine_bridge.py).

The engine itself is covered by Epic 4's scenario suite. What is asserted here is the wiring:
the confidence-score writeback is atomic and always explained (FR-5.3 / AD-9), the raw score
never leaks as a label, reads are ``user_id``-scoped (AD-4), and the Dashboard's and the
Commitments page's figures come from one computation so they cannot disagree.

Session-injected against in-memory SQLite, so no Reflex app is needed.
"""
from __future__ import annotations

import datetime
from decimal import Decimal

import pytest
import sqlmodel

import finance_app.models  # noqa: F401 — registers all app tables
from finance_app.models import Commitment, CommitmentSuggestion, ScoreEvent, Transaction
from finance_app.state.engine_bridge import (
    STALE_AFTER_DAYS,
    compute_dashboard,
    confidence_label,
    confidence_variant,
    detect_commitment_candidates,
    humanize_since,
    latest_score_event,
    load_commitments,
    load_transactions,
    recent_score_events,
    sync_confidence_score,
    to_commitment_records,
)
from reflex_local_auth.user import LocalUser


@pytest.fixture
def session(tmp_path):
    engine = sqlmodel.create_engine(f"sqlite:///{tmp_path / 'bridge.db'}")
    sqlmodel.SQLModel.metadata.create_all(engine)
    with sqlmodel.Session(engine) as s:
        yield s


def make_user(session, email: str) -> LocalUser:
    user = LocalUser(  # type: ignore[call-arg]
        username=email, password_hash=LocalUser.hash_password("supersecret8"), enabled=True
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def add_txn(session, user_id, date, description, amount, direction="debit", balance=None):
    session.add(
        Transaction(  # type: ignore[call-arg]
            user_id=user_id,
            date=date,
            description_raw=description,
            amount=Decimal(amount),
            direction=direction,
            balance_after=Decimal(balance) if balance is not None else None,
        )
    )
    session.commit()


def add_commitment(session, user_id, name, amount, due_day, criticality="important"):
    row = Commitment(  # type: ignore[call-arg]
        user_id=user_id,
        name=name,
        amount=Decimal(amount),
        due_day=due_day,
        criticality=criticality,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def seed_statement(session, user_id, balance="25040"):
    """A statement with a salary credit so the engine has a payday to work with."""
    add_txn(session, user_id, "2026-06-01", "UPI-SWIGGY", "450", balance="30000")
    add_txn(
        session, user_id, "2026-06-30", "SALARY ACME CORP", "85000", "credit", balance=balance
    )


class TestDetectCommitmentCandidates:
    """The DB-backed detection path (Story 5.6): reads decided signatures under a user filter."""

    def _seed_emi(self, session, user_id):
        add_txn(session, user_id, "2026-04-05", "HDFC EMI", "8500")
        add_txn(session, user_id, "2026-05-05", "HDFC EMI", "8500")
        add_txn(session, user_id, "2026-06-05", "HDFC EMI", "8500")

    def test_detects_recurring_charge(self, session):
        user = make_user(session, "emi@example.com")
        self._seed_emi(session, user.id)

        candidates = detect_commitment_candidates(session, user.id)

        assert len(candidates) == 1
        assert candidates[0].signature == "hdfc emi@5"
        assert candidates[0].amount == Decimal("8500")

    def test_decided_signature_is_excluded(self, session):
        user = make_user(session, "emi2@example.com")
        self._seed_emi(session, user.id)
        session.add(
            CommitmentSuggestion(  # type: ignore[call-arg]
                user_id=user.id, signature="hdfc emi@5", status="dismissed"
            )
        )
        session.commit()

        assert detect_commitment_candidates(session, user.id) == []

    def test_another_users_dismissal_does_not_leak(self, session):
        """A dismissal is scoped to its owner (AD-4) — user B still sees the suggestion."""
        user_a = make_user(session, "a@example.com")
        user_b = make_user(session, "b@example.com")
        self._seed_emi(session, user_a.id)
        self._seed_emi(session, user_b.id)
        session.add(
            CommitmentSuggestion(  # type: ignore[call-arg]
                user_id=user_a.id, signature="hdfc emi@5", status="dismissed"
            )
        )
        session.commit()

        assert detect_commitment_candidates(session, user_a.id) == []
        assert len(detect_commitment_candidates(session, user_b.id)) == 1


class TestConfidenceLabels:
    @pytest.mark.parametrize(
        "score,label,variant",
        [
            (100, "Well prepared", "green"),
            (70, "Well prepared", "green"),
            (69, "On track", "amber"),
            (40, "On track", "amber"),
            (39, "Watch this", "red-amber"),
            (0, "Watch this", "red-amber"),
        ],
    )
    def test_bands_map_score_to_label_and_variant(self, score, label, variant):
        assert confidence_label(score) == label
        assert confidence_variant(score) == variant

    def test_a_shortfall_score_can_never_read_as_well_prepared(self):
        # CS-4: Epic 4 caps a not-safety_ok score at 20, so every shortfall lands in the
        # bottom band. A ₹0 Safe-to-Spend beside "Well prepared" is structurally impossible.
        for score in range(0, 21):
            assert confidence_label(score) == "Watch this"


class TestTimestampConvention:
    """Stored timestamps are naive UTC (``models._utcnow``), matching the naive DB columns.

    Writing a tz-aware value into a naive column drops the offset silently, so the read side got
    a naive value anyway and any comparison against an aware ``now()`` raised ``TypeError``.
    Flagged in the Story 1.2 review to be settled "when timestamps are first consumed" — that is
    the Epic 5 drill-in panel.
    """

    def test_utcnow_is_naive(self):
        from finance_app.models import _utcnow

        assert _utcnow().tzinfo is None

    def test_utcnow_is_actually_utc_not_local_time(self):
        from finance_app.models import _utcnow

        drift = abs(
            (_utcnow() - datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)).total_seconds()
        )
        assert drift < 5  # not a local-time naive value in a non-UTC zone

    def test_a_persisted_score_event_round_trips_as_naive_and_renders(self, session):
        user = make_user(session, "a@x.com")
        seed_statement(session, user.id)
        event = sync_confidence_score(
            session, user.id, compute_dashboard(session, user.id).evidence, trigger_event="upload"
        )
        assert event.timestamp.tzinfo is None
        # The drill-in compares this against an aware now(); it must not raise.
        assert humanize_since(event.timestamp) == "just now"


class TestHumanizeSince:
    def test_renders_relative_times_for_the_drill_in_panel(self):
        now = datetime.datetime(2026, 7, 10, 12, 0, tzinfo=datetime.timezone.utc)
        assert humanize_since(now - datetime.timedelta(seconds=30), now=now) == "just now"
        assert humanize_since(now - datetime.timedelta(minutes=5), now=now) == "5 minutes ago"
        assert humanize_since(now - datetime.timedelta(hours=2), now=now) == "2 hours ago"
        assert humanize_since(now - datetime.timedelta(days=1), now=now) == "1 day ago"
        assert humanize_since(now - datetime.timedelta(days=3), now=now) == "3 days ago"

    def test_a_naive_db_timestamp_is_treated_as_utc_and_does_not_raise(self):
        # models._utcnow() writes aware UTC into a naive column, so reads come back naive.
        # Comparing naive to aware raises TypeError; the drill-in must never crash on that.
        now = datetime.datetime(2026, 7, 10, 12, 0, tzinfo=datetime.timezone.utc)
        naive = datetime.datetime(2026, 7, 10, 10, 0)  # no tzinfo
        assert humanize_since(naive, now=now) == "2 hours ago"

    def test_a_future_timestamp_clamps_rather_than_rendering_a_negative_age(self):
        now = datetime.datetime(2026, 7, 10, 12, 0, tzinfo=datetime.timezone.utc)
        assert humanize_since(now + datetime.timedelta(hours=1), now=now) == "just now"


class TestUserScopedReads:
    def test_transactions_are_scoped_to_their_owner(self, session):
        user_a, user_b = make_user(session, "a@x.com"), make_user(session, "b@x.com")
        add_txn(session, user_b.id, "2026-06-01", "SWIGGY", "250")
        assert load_transactions(session, user_a.id) == []
        assert len(load_transactions(session, user_b.id)) == 1

    def test_commitments_are_scoped_to_their_owner(self, session):
        user_a, user_b = make_user(session, "a@x.com"), make_user(session, "b@x.com")
        add_commitment(session, user_b.id, "HDFC EMI", "8500", 15)
        assert load_commitments(session, user_a.id) == []
        assert len(load_commitments(session, user_b.id)) == 1

    def test_user_b_commitments_never_reserve_against_user_a_balance(self, session):
        # The aggregate path, not just the row read: B's ₹20,000 EMI must not depress A's STS.
        user_a, user_b = make_user(session, "a@x.com"), make_user(session, "b@x.com")
        seed_statement(session, user_a.id)
        add_commitment(session, user_b.id, "B's huge EMI", "20000", 15, "critical")

        data = compute_dashboard(session, user_a.id)
        assert data.evidence.reserved_total == Decimal("0")

    def test_score_events_are_scoped_to_their_owner(self, session):
        user_a, user_b = make_user(session, "a@x.com"), make_user(session, "b@x.com")
        seed_statement(session, user_b.id)
        data = compute_dashboard(session, user_b.id)
        sync_confidence_score(session, user_b.id, data.evidence, trigger_event="upload")

        assert latest_score_event(session, user_a.id) is None
        assert latest_score_event(session, user_b.id) is not None


class TestCommitmentRecordMapping:
    def test_db_rows_map_to_engine_records_preserving_decimal_amounts(self, session):
        user = make_user(session, "a@x.com")
        add_commitment(session, user.id, "HDFC EMI", "8500.50", 15, "critical")
        records = to_commitment_records(load_commitments(session, user.id))
        assert len(records) == 1
        assert records[0].name == "HDFC EMI"
        assert records[0].amount == Decimal("8500.50")
        assert isinstance(records[0].amount, Decimal)  # AD-8: never float
        assert records[0].due_day == 15
        assert records[0].criticality == "critical"


class TestComputeDashboard:
    def test_a_user_with_no_transactions_has_no_data_and_does_not_crash(self, session):
        user = make_user(session, "a@x.com")
        data = compute_dashboard(session, user.id)
        assert data.has_data is False
        assert data.statement_end_date is None
        assert data.transaction_count == 0

    def test_statement_end_date_drives_freshness_not_today(self, session):
        user = make_user(session, "a@x.com")
        seed_statement(session, user.id)
        data = compute_dashboard(session, user.id)
        assert data.statement_end_date == datetime.date(2026, 6, 30)

    def test_an_old_statement_is_flagged_stale(self, session):
        user = make_user(session, "a@x.com")
        old = datetime.date.today() - datetime.timedelta(days=STALE_AFTER_DAYS + 1)
        add_txn(session, user.id, old.isoformat(), "UPI-SWIGGY", "450", balance="18000")
        assert compute_dashboard(session, user.id).is_stale is True

    def test_a_recent_statement_is_not_flagged_stale(self, session):
        user = make_user(session, "a@x.com")
        recent = datetime.date.today() - datetime.timedelta(days=2)
        add_txn(session, user.id, recent.isoformat(), "UPI-SWIGGY", "450", balance="18000")
        assert compute_dashboard(session, user.id).is_stale is False

    def test_a_commitment_reduces_safe_to_spend(self, session):
        user = make_user(session, "a@x.com")
        seed_statement(session, user.id)
        before = compute_dashboard(session, user.id).evidence.safe_to_spend_today

        add_commitment(session, user.id, "HDFC EMI", "8500", 15, "critical")
        after = compute_dashboard(session, user.id)

        assert after.evidence.reserved_total == Decimal("8500")
        assert after.evidence.safe_to_spend_today < before

    def test_the_detected_salary_surfaces_as_a_next_income_date(self, session):
        user = make_user(session, "a@x.com")
        seed_statement(session, user.id)
        data = compute_dashboard(session, user.id)
        # Salary on 30 Jun -> next payday projected to 30 Jul; the briefing needs to name it.
        assert data.next_income_date == datetime.date(2026, 7, 30)
        assert data.evidence.safe_to_spend_after_income is not None

    def test_no_salary_yields_no_income_date_and_an_honest_flag(self, session):
        user = make_user(session, "a@x.com")
        add_txn(session, user.id, "2026-06-01", "UPI-SWIGGY", "450", balance="20000")
        data = compute_dashboard(session, user.id)
        assert data.next_income_date is None
        assert data.evidence.safe_to_spend_after_income is None
        assert "no_income_detected" in data.evidence.data_quality_flags


class TestScoreWriteback:
    """FR-5.3 / AD-9 — the score and its explanation are written together, or not at all."""

    def test_the_first_computation_always_writes_an_explained_row(self, session):
        user = make_user(session, "a@x.com")
        seed_statement(session, user.id)
        data = compute_dashboard(session, user.id)

        event = sync_confidence_score(
            session, user.id, data.evidence, trigger_event="statement_upload"
        )
        assert event.id is not None
        assert event.trigger_event == "statement_upload"
        assert event.explanation  # never blank — an unexplained score is unreachable
        assert event.suggested_action

    def test_cold_start_computes_a_real_score_not_a_fake_neutral_fifty(self, session):
        # FR-5.4: the score is real from the first upload.
        user = make_user(session, "a@x.com")
        seed_statement(session, user.id)
        data = compute_dashboard(session, user.id)
        event = sync_confidence_score(session, user.id, data.evidence, trigger_event="upload")
        assert event.score != 50 or event.explanation  # a real, explained figure
        assert event.delta == event.score  # first row: delta measured from zero

    def test_an_unchanged_score_writes_no_new_row(self, session):
        # Nothing changed, so there is nothing to explain. The drill-in stays meaningful.
        user = make_user(session, "a@x.com")
        seed_statement(session, user.id)
        data = compute_dashboard(session, user.id)

        first = sync_confidence_score(session, user.id, data.evidence, trigger_event="upload")
        second = sync_confidence_score(
            session, user.id, data.evidence, trigger_event="dashboard_view"
        )
        assert second.id == first.id
        assert len(recent_score_events(session, user.id)) == 1

    def test_adding_a_commitment_moves_the_score_and_records_why(self, session):
        user = make_user(session, "a@x.com")
        seed_statement(session, user.id)
        first = sync_confidence_score(
            session,
            user.id,
            compute_dashboard(session, user.id).evidence,
            trigger_event="statement_upload",
        )

        add_commitment(session, user.id, "HDFC EMI", "8500", 15, "critical")
        second = sync_confidence_score(
            session,
            user.id,
            compute_dashboard(session, user.id).evidence,
            trigger_event="commitment_added",
        )

        assert second.id != first.id
        assert second.trigger_event == "commitment_added"
        assert second.delta == second.score - first.score
        assert len(recent_score_events(session, user.id)) == 2

    def test_the_ui_score_is_the_latest_row_not_a_bare_column(self, session):
        user = make_user(session, "a@x.com")
        seed_statement(session, user.id)
        sync_confidence_score(
            session, user.id, compute_dashboard(session, user.id).evidence, trigger_event="a"
        )
        add_commitment(session, user.id, "HDFC EMI", "8500", 15, "critical")
        newest = sync_confidence_score(
            session, user.id, compute_dashboard(session, user.id).evidence, trigger_event="b"
        )
        assert latest_score_event(session, user.id).id == newest.id

    def test_every_drill_in_row_corresponds_to_a_real_db_row(self, session):
        user = make_user(session, "a@x.com")
        seed_statement(session, user.id)
        sync_confidence_score(
            session, user.id, compute_dashboard(session, user.id).evidence, trigger_event="a"
        )
        add_commitment(session, user.id, "HDFC EMI", "8500", 15, "critical")
        sync_confidence_score(
            session, user.id, compute_dashboard(session, user.id).evidence, trigger_event="b"
        )

        events = recent_score_events(session, user.id)
        persisted = session.exec(
            sqlmodel.select(ScoreEvent).where(ScoreEvent.user_id == user.id)
        ).all()
        assert len(events) == len(persisted) == 2
        assert all(event.explanation for event in events)

    def test_drill_in_rows_are_newest_first(self, session):
        user = make_user(session, "a@x.com")
        seed_statement(session, user.id)
        sync_confidence_score(
            session, user.id, compute_dashboard(session, user.id).evidence, trigger_event="first"
        )
        add_commitment(session, user.id, "HDFC EMI", "8500", 15, "critical")
        sync_confidence_score(
            session, user.id, compute_dashboard(session, user.id).evidence, trigger_event="second"
        )
        events = recent_score_events(session, user.id)
        assert events[0].trigger_event == "second"

    def test_a_zero_safe_to_spend_never_coexists_with_well_prepared(self, session):
        # CS-4 asserted end to end, through the real DB path.
        user = make_user(session, "a@x.com")
        add_txn(session, user.id, "2026-06-01", "UPI-SWIGGY", "450", balance="5000")
        add_commitment(session, user.id, "Huge EMI", "50000", 15, "critical")

        data = compute_dashboard(session, user.id)
        event = sync_confidence_score(session, user.id, data.evidence, trigger_event="upload")

        assert data.evidence.safe_to_spend_today == Decimal("0")
        assert data.evidence.safety_ok is False
        assert confidence_label(event.score) != "Well prepared"


class TestDashboardAndCommitmentsAgree:
    def test_both_screens_read_the_same_engine_figures(self, session):
        """The Commitments impact bar and the Dashboard hero must never disagree.

        Both call ``compute_dashboard``; this pins that they produce identical figures for the
        same data, which is the reason the bridge exists rather than two parallel queries.
        """
        user = make_user(session, "a@x.com")
        seed_statement(session, user.id)
        add_commitment(session, user.id, "HDFC EMI", "8500", 15, "critical")

        dashboard_view = compute_dashboard(session, user.id)
        commitments_view = compute_dashboard(session, user.id)

        assert (
            dashboard_view.evidence.safe_to_spend_today
            == commitments_view.evidence.safe_to_spend_today
        )
        assert dashboard_view.evidence.reserved_total == commitments_view.evidence.reserved_total

    def test_reserved_total_is_not_the_naive_sum_of_all_commitments(self, session):
        """The impact bar shows what is *ring-fenced this cycle*, not every commitment.

        A bill due after the next payday is next cycle's problem. Summing all commitments would
        over-report protection and understate Safe-to-Spend.
        """
        user = make_user(session, "a@x.com")
        seed_statement(session, user.id)  # payday projected to 30 Jul
        add_commitment(session, user.id, "Due before payday", "5000", 15, "critical")

        data = compute_dashboard(session, user.id)
        assert data.evidence.reserved_total == Decimal("5000")
