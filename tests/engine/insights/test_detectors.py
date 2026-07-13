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
    MIN_DATA_MONTHS_FOR_TREND,
    PACE_IMPROVED_MIN_PCT,
    CommitmentRecord,
    CommitmentsCoveredDetector,
    DeathBySmallPurchasesDetector,
    InsightCandidate,
    InsightContext,
    InsightDetector,
    PostPaydaySpikeDetector,
    SpendingPaceImprovedDetector,
    SubscriptionEndedDetector,
    TxnRecord,
    UpcomingCommitmentCollisionDetector,
    WeekendWeekdayPaceDetector,
    ZombieSubscriptionDetector,
    run_all_detectors,
)
from services.engine.insights.detectors import _infer_paydays, data_months
from services.utils.enums import Criticality, Direction, Tone

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


def test_post_payday_spike_evaluates_most_recent_cycle_not_a_stale_earlier_one() -> None:
    """Regression: the detector used to anchor on ``paydays[0]`` (the earliest payday)
    and pool every other month's own spend into the "baseline" — so a real spike from
    month 1 kept firing forever even after spending normalized in the latest month.
    """
    ctx = InsightContext(
        transactions=(
            # May: genuine post-payday spike (would fire if evaluated alone).
            _txn("2026-05-01", "50000", direction=Direction.credit.value),
            _txn("2026-05-01", "3000"),
            _txn("2026-05-02", "2500"),
            _txn("2026-05-03", "2000"),
            _txn("2026-05-10", "200"),
            _txn("2026-05-20", "200"),
            # June: the latest cycle — even spending, no real spike.
            _txn("2026-06-01", "50000", direction=Direction.credit.value),
            _txn("2026-06-01", "500"),
            _txn("2026-06-02", "500"),
            _txn("2026-06-03", "500"),
            _txn("2026-06-10", "500"),
            _txn("2026-06-20", "500"),
        )
    )
    assert PostPaydaySpikeDetector().detect(ctx) == []


def test_post_payday_spike_silent_with_fewer_than_two_evidence_points() -> None:
    """A single post-payday debit can't honestly satisfy the 2-3 evidence-point
    contract (AC #3), so the detector abstains rather than firing thin evidence."""
    ctx = InsightContext(
        transactions=(
            _txn("2026-06-01", "50000", direction=Direction.credit.value),
            _txn("2026-06-01", "5000"),  # lone post-payday debit
            _txn("2026-06-15", "50"),
            _txn("2026-06-20", "50"),
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


def test_zombie_subscription_median_averages_the_two_middle_amounts() -> None:
    """Regression: for the minimum 2-occurrence case, ``sorted(amounts)[len//2]`` picked
    the upper value, not a true median, skewing the ``monthly_amount`` cited verbatim by
    the narrator."""
    ctx = InsightContext(
        transactions=(
            _txn("2026-05-05", "499", merchant="Netflix"),
            _txn("2026-06-04", "501", merchant="Netflix"),
        )
    )
    result = ZombieSubscriptionDetector().detect(ctx)
    assert len(result) == 1
    assert result[0].metrics["monthly_amount"] == Decimal("500")


def test_zombie_subscription_does_not_merge_unrelated_blank_merchant_debits() -> None:
    """Two unrelated cash-style debits with no merchant identity (no merchant_normalized,
    no description) must never be reported as one recurring 'Unknown' subscription."""
    ctx = InsightContext(
        transactions=(
            _txn("2026-05-05", "499"),
            _txn("2026-06-04", "499"),
        )
    )
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


def test_weekend_pace_silent_with_only_a_single_weekend_day_of_data() -> None:
    """A lone weekend transaction is not enough sample size to honestly claim a pace
    pattern (AC #9's data-honesty principle) — mirrors the min-occurrence gates every
    sibling detector already has."""
    ctx = InsightContext(
        transactions=(
            _txn("2026-06-01", "200"),  # Mon
            _txn("2026-06-02", "200"),  # Tue
            _txn("2026-06-06", "3000"),  # Sat — only one weekend day of data
        )
    )
    assert WeekendWeekdayPaceDetector().detect(ctx) == []


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
    assert 2 <= len(result[0].evidence) <= 3


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


def test_collision_evidence_always_includes_current_balance_and_worst_commitment() -> None:
    """Regression: evidence used to be sliced in due-date order while the cited
    ``projected_shortfall`` was computed over ALL colliding commitments — with more than
    MAX_EVIDENCE_POINTS colliding, the commitment actually driving the shortfall could be
    silently excluded from the evidence shown alongside it."""
    ctx = InsightContext(
        transactions=(_txn("2026-06-20", "500", balance="100"),),
        commitments=(
            CommitmentRecord("Bill A", Decimal("500"), date(2026, 6, 21), Criticality.important.value),
            CommitmentRecord("Bill B", Decimal("500"), date(2026, 6, 22), Criticality.important.value),
            CommitmentRecord("Bill C", Decimal("500"), date(2026, 6, 23), Criticality.important.value),
            CommitmentRecord("Bill D", Decimal("500"), date(2026, 6, 24), Criticality.important.value),
        ),
        as_of=date(2026, 6, 20),
    )
    result = UpcomingCommitmentCollisionDetector().detect(ctx)
    assert len(result) == 1
    candidate = result[0]
    # Running balance depletes monotonically A->B->C->D, so Bill D drives the worst
    # (most negative) projected balance -- it must appear in the evidence shown.
    assert candidate.metrics["projected_shortfall"] == Decimal("1900")
    assert 2 <= len(candidate.evidence) <= 3
    merchants = {ep.merchant for ep in candidate.evidence}
    assert "Bill D" in merchants
    assert "Current balance" in merchants


# --------------------------------------------------------------------------------------
# _infer_paydays, data_months & InsightCandidate hashability (helper-level regressions)
# --------------------------------------------------------------------------------------
def test_infer_paydays_prefers_recurring_amount_over_a_one_off_larger_credit() -> None:
    """A single one-off transfer that happens to exceed the real recurring salary must
    not be mistaken for payday when a smaller amount actually recurs."""
    ctx = InsightContext(
        transactions=(
            _txn("2026-05-15", "60000", direction=Direction.credit.value),  # one-off
            _txn("2026-05-01", "50000", direction=Direction.credit.value),  # real salary
            _txn("2026-06-01", "50000", direction=Direction.credit.value),  # real salary
        )
    )
    assert _infer_paydays(ctx) == [date(2026, 5, 1), date(2026, 6, 1)]


def test_infer_paydays_falls_back_to_the_lone_credit_when_nothing_recurs() -> None:
    """A brand-new user with exactly one month of history has no recurring credit yet --
    the largest (and only) credit is still the best honest guess at payday."""
    ctx = InsightContext(
        transactions=(_txn("2026-06-01", "50000", direction=Direction.credit.value),)
    )
    assert _infer_paydays(ctx) == [date(2026, 6, 1)]


def test_data_months_computes_the_calendar_span_not_just_distinct_months_touched() -> None:
    """AC #9: 'computed from the span of ctx.transactions' -- a January + June
    transaction pair spans 6 months, not the 2 distinct months actually touched."""
    txns = (_txn("2026-01-15", "100"), _txn("2026-06-10", "100"))
    assert data_months(txns) == 6


def test_insight_candidate_is_hashable_despite_the_metrics_mapping() -> None:
    """Regression: ``metrics`` is a mutable dict on a frozen dataclass with the default
    auto-generated __hash__ -- calling hash() used to raise TypeError, a landmine for any
    future dedup/set usage (e.g. Story 7.3)."""
    candidate = InsightCandidate(
        pattern_name="Test pattern",
        severity=Criticality.important.value,
        evidence=(),
        metrics={"foo": Decimal("1")},
        data_months=1,
    )
    hash(candidate)  # must not raise


# --------------------------------------------------------------------------------------
# Protocol, orchestrator & demo fixture
# --------------------------------------------------------------------------------------
def test_all_detectors_conform_to_protocol_and_map_1to1_to_patterns() -> None:
    assert len(ALL_DETECTORS) == 8
    for detector in ALL_DETECTORS:
        assert isinstance(detector, InsightDetector)
        assert isinstance(detector.pattern_name, str) and detector.pattern_name
    names = {d.pattern_name for d in ALL_DETECTORS}
    assert names == {
        # the five FR-8.1 warnings ...
        "Post-payday spike",
        "Death by small purchases",
        "Zombie subscriptions",
        "Weekend vs weekday pace",
        "Upcoming commitment collision",
        # ... and the wins, so the feed is not structurally incapable of good news
        "Subscription ended",
        "Commitments covered",
        "Spending pace improved",
    }


def test_run_all_detectors_empty_context_returns_empty_list() -> None:
    assert run_all_detectors(InsightContext()) == []


def _demo_context() -> InsightContext:
    """June-2026 Priya-style month: salary, a post-payday cluster, weekend splurges, a
    long tail of small purchases, and a genuine Netflix subscription recurring from the
    prior month — plus a rent commitment due right before month-end. 24 transactions,
    matching AC #7's spec text exactly (one salary credit, >=1 recurring subscription,
    a post-payday cluster)."""
    txns: list[TxnRecord] = [
        _txn("2026-06-01", "50000", direction=Direction.credit.value, balance="50000"),
        # recurring subscription: same charge ~monthly (May -> June), merchant-tagged
        _txn("2026-05-05", "649", merchant="Netflix"),
        _txn("2026-06-05", "649", merchant="Netflix"),
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


# ======================================================================================
# The win detectors (2026-07-12).
#
# All five FR-8.1 detectors above are negative-valence: not one of them can ever tell a user
# they did something right. These three can. Same one-true-positive / one-true-negative
# convention as the warnings (AC #6).
# ======================================================================================


# --------------------------------------------------------------------------------------
# Subscription ended -- and the zombie-staleness bug it exposed
# --------------------------------------------------------------------------------------
def test_subscription_ended_fires_when_the_next_charge_never_came() -> None:
    """Netflix charged monthly, then stopped. Four months later it is plainly cancelled."""
    ctx = InsightContext(
        transactions=(
            _txn("2026-01-05", "499", merchant="Netflix"),
            _txn("2026-02-05", "499", merchant="Netflix"),
            _txn("2026-03-05", "499", merchant="Netflix"),
        ),
        as_of=date(2026, 7, 1),  # ~4 months past the last charge
    )
    out = SubscriptionEndedDetector().detect(ctx)

    assert len(out) == 1
    assert out[0].pattern_name == "Subscription ended"
    assert out[0].tone == Tone.win.value
    assert out[0].metrics["merchant"] == "Netflix"
    assert out[0].metrics["monthly_amount"] == Decimal("499")
    assert out[0].metrics["last_charged"] == "2026-03-05"


def test_subscription_ended_silent_while_the_subscription_is_still_live() -> None:
    ctx = InsightContext(
        transactions=(
            _txn("2026-05-05", "499", merchant="Netflix"),
            _txn("2026-06-05", "499", merchant="Netflix"),
        ),
        as_of=date(2026, 6, 20),  # last charge only 15 days ago -- still running
    )
    assert SubscriptionEndedDetector().detect(ctx) == []


def test_a_cancelled_subscription_is_never_also_reported_as_a_live_zombie() -> None:
    """The regression this refactor exists to fix.

    Before the staleness check, ZombieSubscriptionDetector had no notion of "when" -- a
    subscription cancelled a year ago still satisfied "2+ near-equal charges at monthly
    cadence" forever, and was reported as an active drain on the user's money. Once
    SubscriptionEndedDetector existed, the same merchant fired *both*: the feed would have
    claimed a subscription was simultaneously live and cancelled.

    The two detectors must partition the same recurring series, never overlap.
    """
    ctx = InsightContext(
        transactions=(
            _txn("2026-01-05", "499", merchant="Netflix"),
            _txn("2026-02-05", "499", merchant="Netflix"),
            _txn("2026-03-05", "499", merchant="Netflix"),
        ),
        as_of=date(2026, 7, 1),
    )
    zombies = ZombieSubscriptionDetector().detect(ctx)
    ended = SubscriptionEndedDetector().detect(ctx)

    assert zombies == []  # cancelled -- NOT a live drain (this failed before the fix)
    assert len(ended) == 1  # ... it is a win
    # And the partition holds through the orchestrator, which is what the page actually sees.
    names = [c.pattern_name for c in run_all_detectors(ctx)]
    assert "Zombie subscriptions" not in names
    assert "Subscription ended" in names


def test_a_live_subscription_is_still_a_zombie_and_never_reported_as_ended() -> None:
    """The other half of the partition -- the staleness fix must not silence the real thing."""
    ctx = InsightContext(
        transactions=(
            _txn("2026-05-05", "499", merchant="Netflix"),
            _txn("2026-06-05", "499", merchant="Netflix"),
        ),
        as_of=date(2026, 6, 20),
    )
    assert len(ZombieSubscriptionDetector().detect(ctx)) == 1
    assert SubscriptionEndedDetector().detect(ctx) == []


# --------------------------------------------------------------------------------------
# Commitments covered
# --------------------------------------------------------------------------------------
def test_commitments_covered_fires_when_the_balance_absorbs_every_upcoming_bill() -> None:
    ctx = InsightContext(
        transactions=(_txn("2026-06-10", "500", balance="20000"),),
        commitments=(
            CommitmentRecord(name="Rent", amount=Decimal("12000"), due_date=date(2026, 6, 14)),
            CommitmentRecord(name="Phone", amount=Decimal("800"), due_date=date(2026, 6, 15)),
        ),
        as_of=date(2026, 6, 12),
    )
    out = CommitmentsCoveredDetector().detect(ctx)

    assert len(out) == 1
    assert out[0].tone == Tone.win.value
    assert out[0].metrics["covered_count"] == 2
    assert out[0].metrics["due_total"] == Decimal("12800")
    assert out[0].metrics["headroom"] == Decimal("7200")  # 20000 - 12800
    # Leads with the balance doing the covering, same evidence shape as the collision twin.
    assert out[0].evidence[0].merchant == "Current balance"


def test_commitments_covered_silent_when_a_bill_would_collide() -> None:
    """Fires precisely when UpcomingCommitmentCollisionDetector does not -- never both."""
    ctx = InsightContext(
        transactions=(_txn("2026-06-10", "500", balance="5000"),),
        commitments=(
            CommitmentRecord(name="Rent", amount=Decimal("12000"), due_date=date(2026, 6, 14)),
        ),
        as_of=date(2026, 6, 12),
    )
    assert CommitmentsCoveredDetector().detect(ctx) == []
    assert len(UpcomingCommitmentCollisionDetector().detect(ctx)) == 1


def test_commitments_covered_silent_when_nothing_is_due() -> None:
    """"All zero of your bills are covered" is not a win, it is noise."""
    ctx = InsightContext(
        transactions=(_txn("2026-06-10", "500", balance="20000"),),
        commitments=(
            CommitmentRecord(name="Rent", amount=Decimal("12000"), due_date=date(2026, 9, 1)),
        ),
        as_of=date(2026, 6, 12),  # Sept rent is far outside the 7-day lookahead
    )
    assert CommitmentsCoveredDetector().detect(ctx) == []


# --------------------------------------------------------------------------------------
# Spending pace improved
# --------------------------------------------------------------------------------------
def test_spending_pace_improved_fires_when_the_recent_rate_drops_below_baseline() -> None:
    """Baseline (Apr): ~₹1,000/day. Recent 30d (June): ~₹100/day. A real, honest win."""
    baseline = tuple(_txn(f"2026-04-{d:02d}", "1000") for d in range(1, 29))
    recent = tuple(_txn(f"2026-06-{d:02d}", "100") for d in range(1, 29))
    ctx = InsightContext(transactions=baseline + recent, as_of=date(2026, 6, 28))

    out = SpendingPaceImprovedDetector().detect(ctx)

    assert len(out) == 1
    assert out[0].tone == Tone.win.value
    assert out[0].metrics["drop_pct"] > PACE_IMPROVED_MIN_PCT
    # A rate has no transaction to cite -- the card renders without an evidence block.
    assert out[0].evidence == ()


def test_spending_pace_improved_silent_when_spending_held_steady() -> None:
    steady = tuple(_txn(f"2026-04-{d:02d}", "1000") for d in range(1, 29)) + tuple(
        _txn(f"2026-06-{d:02d}", "1000") for d in range(1, 29)
    )
    ctx = InsightContext(transactions=steady, as_of=date(2026, 6, 28))
    assert SpendingPaceImprovedDetector().detect(ctx) == []


def test_spending_pace_improved_refuses_to_claim_a_trend_on_thin_history() -> None:
    """One quiet week is not a trend. A congratulation the data can't support is exactly the
    dishonesty this product exists not to commit -- so it stays silent below the threshold."""
    ctx = InsightContext(
        transactions=tuple(_txn(f"2026-06-{d:02d}", "100") for d in range(1, 8)),
        as_of=date(2026, 6, 8),
    )
    assert data_months(ctx.transactions) < MIN_DATA_MONTHS_FOR_TREND
    assert SpendingPaceImprovedDetector().detect(ctx) == []


# --------------------------------------------------------------------------------------
# The tone axis itself
# --------------------------------------------------------------------------------------
def test_every_fr81_warning_detector_still_emits_the_watch_tone() -> None:
    """The `tone` field defaults to `watch`, which is what let the five original detectors
    stay untouched. If a refactor ever flips that default, the whole feed silently becomes
    good news -- so pin it."""
    ctx = _demo_context()
    for candidate in run_all_detectors(ctx):
        if candidate.pattern_name in {
            "Subscription ended",
            "Commitments covered",
            "Spending pace improved",
        }:
            assert candidate.tone == Tone.win.value
        else:
            assert candidate.tone == Tone.watch.value
