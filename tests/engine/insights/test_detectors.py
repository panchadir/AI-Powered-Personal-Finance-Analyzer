"""Unit suite for the FR-8.1 insight detectors (Story 7.1).

One true-positive + one true-negative per detector (AC #6), a demo-representative fixture
that fires ≥3 detectors (AC #7), and protocol/orchestrator checks. Lives under
``tests/engine/`` so it inherits that package's autouse ``_forbid_anthropic`` fixture —
any Anthropic client construction raises, proving zero LLM calls (AD-1, AC #6/#11).
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from services.engine.insights import (
    ALL_DETECTORS,
    CommitmentRecord,
    DeathBySmallPurchasesDetector,
    InsightContext,
    InsightDetector,
    PostPaydaySpikeDetector,
    TxnRecord,
    UpcomingCommitmentCollisionDetector,
    WeekendWeekdayPaceDetector,
    ZombieSubscriptionDetector,
    run_all_detectors,
)
from services.utils.enums import Criticality, Direction

# June 2026 calendar anchor: Jun 1 = Mon; Sat/Sun = Jun 6/7, 13/14, 20/21, 27/28.


def _txn(
    day: str,
    amount: str,
    *,
    direction: str = Direction.debit.value,
    merchant: str | None = None,
    balance: str | None = None,
) -> TxnRecord:
    return TxnRecord(
        date=day,
        amount=Decimal(amount),
        direction=direction,
        description_raw=merchant or "",
        merchant_normalized=merchant,
        balance_after=Decimal(balance) if balance is not None else None,
    )


# --------------------------------------------------------------------------------------
# Post-payday spike
# --------------------------------------------------------------------------------------
def test_post_payday_spike_fires_when_post_payday_rate_exceeds_baseline() -> None:
    ctx = InsightContext(
        transactions=(
            _txn("2026-06-01", "50000", direction=Direction.credit.value),  # salary
            _txn("2026-06-01", "3000"),
            _txn("2026-06-02", "2500"),
            _txn("2026-06-03", "2000"),
            _txn("2026-06-12", "200"),
            _txn("2026-06-20", "200"),
        )
    )
    result = PostPaydaySpikeDetector().detect(ctx)
    assert len(result) == 1
    candidate = result[0]
    assert candidate.pattern_name == "Post-payday spike"
    assert candidate.metrics["spike_pct"] >= Decimal("40")
    assert 2 <= len(candidate.evidence) <= 3


def test_post_payday_spike_silent_when_spending_is_even() -> None:
    ctx = InsightContext(
        transactions=(
            _txn("2026-06-01", "50000", direction=Direction.credit.value),
            _txn("2026-06-01", "500"),
            _txn("2026-06-08", "500"),
            _txn("2026-06-15", "500"),
            _txn("2026-06-22", "500"),
            _txn("2026-06-29", "500"),
        )
    )
    assert PostPaydaySpikeDetector().detect(ctx) == []


# --------------------------------------------------------------------------------------
# Death by small purchases
# --------------------------------------------------------------------------------------
def test_death_by_small_purchases_fires_on_many_small_debits() -> None:
    ctx = InsightContext(
        transactions=tuple(
            _txn(f"2026-06-{day:02d}", "300") for day in range(1, 11)  # 10 × ₹300 = ₹3000
        )
    )
    result = DeathBySmallPurchasesDetector().detect(ctx)
    assert len(result) == 1
    assert result[0].metrics["count"] == 10
    assert result[0].metrics["total"] == Decimal("3000")
    assert 2 <= len(result[0].evidence) <= 3


def test_death_by_small_purchases_silent_when_few_small_debits() -> None:
    ctx = InsightContext(
        transactions=(
            _txn("2026-06-01", "300"),
            _txn("2026-06-05", "250"),
            _txn("2026-06-10", "400"),
        )
    )
    assert DeathBySmallPurchasesDetector().detect(ctx) == []


# --------------------------------------------------------------------------------------
# Zombie subscriptions
# --------------------------------------------------------------------------------------
def test_zombie_subscription_fires_on_monthly_fixed_charge() -> None:
    ctx = InsightContext(
        transactions=(
            _txn("2026-04-05", "499", merchant="Netflix"),
            _txn("2026-05-05", "499", merchant="Netflix"),
            _txn("2026-06-05", "499", merchant="Netflix"),
        )
    )
    result = ZombieSubscriptionDetector().detect(ctx)
    assert len(result) == 1
    assert result[0].metrics["merchant"] == "Netflix"
    assert result[0].metrics["occurrences"] == 3


def test_zombie_subscription_silent_on_single_charge() -> None:
    ctx = InsightContext(transactions=(_txn("2026-06-05", "499", merchant="Netflix"),))
    assert ZombieSubscriptionDetector().detect(ctx) == []


# --------------------------------------------------------------------------------------
# Weekend vs weekday pace
# --------------------------------------------------------------------------------------
def test_weekend_pace_fires_when_weekends_run_hot() -> None:
    ctx = InsightContext(
        transactions=(
            _txn("2026-06-01", "200"),  # Mon
            _txn("2026-06-02", "200"),  # Tue
            _txn("2026-06-03", "200"),  # Wed
            _txn("2026-06-06", "3000"),  # Sat
            _txn("2026-06-07", "3000"),  # Sun
        )
    )
    result = WeekendWeekdayPaceDetector().detect(ctx)
    assert len(result) == 1
    assert result[0].metrics["ratio"] >= Decimal("1.5")
    assert 2 <= len(result[0].evidence) <= 3


def test_weekend_pace_silent_when_pace_is_balanced() -> None:
    ctx = InsightContext(
        transactions=(
            _txn("2026-06-01", "500"),  # Mon
            _txn("2026-06-02", "500"),  # Tue
            _txn("2026-06-03", "500"),  # Wed
            _txn("2026-06-06", "500"),  # Sat
            _txn("2026-06-07", "500"),  # Sun
        )
    )
    assert WeekendWeekdayPaceDetector().detect(ctx) == []


# --------------------------------------------------------------------------------------
# Upcoming commitment collision
# --------------------------------------------------------------------------------------
def test_collision_fires_when_commitment_would_overdraw() -> None:
    ctx = InsightContext(
        transactions=(_txn("2026-06-24", "500", balance="5000"),),
        commitments=(
            CommitmentRecord(
                name="Rent",
                amount=Decimal("8000"),
                due_date=date(2026, 6, 28),
                criticality=Criticality.critical.value,
            ),
        ),
        as_of=date(2026, 6, 25),
    )
    result = UpcomingCommitmentCollisionDetector().detect(ctx)
    assert len(result) == 1
    assert result[0].severity == Criticality.critical.value
    assert result[0].metrics["projected_shortfall"] == Decimal("3000")
    assert len(result[0].evidence) >= 1


def test_collision_silent_when_balance_covers_commitment() -> None:
    ctx = InsightContext(
        transactions=(_txn("2026-06-24", "500", balance="50000"),),
        commitments=(
            CommitmentRecord("Rent", Decimal("8000"), date(2026, 6, 28)),
        ),
        as_of=date(2026, 6, 25),
    )
    assert UpcomingCommitmentCollisionDetector().detect(ctx) == []


def test_collision_silent_without_balance_or_as_of() -> None:
    commitment = CommitmentRecord("Rent", Decimal("8000"), date(2026, 6, 28))
    no_balance = InsightContext(
        transactions=(_txn("2026-06-24", "500"),),
        commitments=(commitment,),
        as_of=date(2026, 6, 25),
    )
    no_as_of = InsightContext(
        transactions=(_txn("2026-06-24", "500", balance="1000"),),
        commitments=(commitment,),
    )
    assert UpcomingCommitmentCollisionDetector().detect(no_balance) == []
    assert UpcomingCommitmentCollisionDetector().detect(no_as_of) == []


# --------------------------------------------------------------------------------------
# Protocol, orchestrator & demo fixture
# --------------------------------------------------------------------------------------
def test_all_detectors_conform_to_protocol_and_map_1to1_to_patterns() -> None:
    assert len(ALL_DETECTORS) == 5
    for detector in ALL_DETECTORS:
        assert isinstance(detector, InsightDetector)
        assert isinstance(detector.pattern_name, str) and detector.pattern_name
    names = {d.pattern_name for d in ALL_DETECTORS}
    assert names == {
        "Post-payday spike",
        "Death by small purchases",
        "Zombie subscriptions",
        "Weekend vs weekday pace",
        "Upcoming commitment collision",
    }


def test_run_all_detectors_empty_context_returns_empty_list() -> None:
    assert run_all_detectors(InsightContext()) == []


def _demo_context() -> InsightContext:
    """June-2026 Priya-style month: salary, a post-payday cluster, weekend splurges, and a
    long tail of small purchases — plus a rent commitment due right before month-end."""
    txns: list[TxnRecord] = [
        _txn("2026-06-01", "50000", direction=Direction.credit.value, balance="50000"),
        # post-payday cluster (Mon–Wed)
        _txn("2026-06-01", "3000"),
        _txn("2026-06-02", "2800"),
        _txn("2026-06-03", "2500"),
        # weekend splurges (Sat/Sun across the month)
        _txn("2026-06-06", "2500"),
        _txn("2026-06-07", "2200"),
        _txn("2026-06-13", "1800"),
        _txn("2026-06-14", "1500"),
        _txn("2026-06-20", "2000"),
        _txn("2026-06-21", "1700"),
        # long tail of small weekday purchases (≤ ₹500)
        _txn("2026-06-09", "300"),
        _txn("2026-06-10", "250"),
        _txn("2026-06-11", "400"),
        _txn("2026-06-12", "350"),
        _txn("2026-06-15", "300"),
        _txn("2026-06-16", "450"),
        _txn("2026-06-17", "200"),
        _txn("2026-06-18", "350"),
        _txn("2026-06-19", "300"),
        _txn("2026-06-22", "400"),
        _txn("2026-06-23", "600"),
        _txn("2026-06-24", "500", balance="4000"),  # latest balance-bearing row
    ]
    return InsightContext(
        transactions=tuple(txns),
        commitments=(
            CommitmentRecord(
                "Rent", Decimal("8000"), date(2026, 6, 28), Criticality.critical.value
            ),
        ),
        as_of=date(2026, 6, 25),
    )


def test_demo_statement_fires_at_least_three_detectors() -> None:
    candidates = run_all_detectors(_demo_context())
    fired = {c.pattern_name for c in candidates}
    assert len(fired) >= 3, f"demo must never be a blank Insights page; fired={fired}"


def test_demo_candidates_are_ordered_by_fr_8_1_detector_sequence() -> None:
    order = [d.pattern_name for d in ALL_DETECTORS]
    fired_in_order = [c.pattern_name for c in run_all_detectors(_demo_context())]
    positions = [order.index(name) for name in fired_in_order]
    assert positions == sorted(positions)


def test_detectors_emit_structured_facts_not_prose() -> None:
    # Evidence carries Decimal amounts + ISO dates (no pre-formatted currency); AD-1/AD-13.
    candidate = PostPaydaySpikeDetector().detect(_demo_context())[0]
    for point in candidate.evidence:
        assert isinstance(point.amount, Decimal)
        assert point.date.count("-") == 2  # ISO YYYY-MM-DD, not a formatted string
