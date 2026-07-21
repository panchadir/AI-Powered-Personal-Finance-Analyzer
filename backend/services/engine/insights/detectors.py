"""The five FR-8.1 insight detectors (Story 7.1).

Pure, deterministic, framework-agnostic — **no LLM touches these** (AD-1) and nothing here
imports ``reflex`` / ``finance_app`` (AD-2). All money arithmetic is :class:`~decimal.Decimal`
(AD-8). Each detector emits :class:`~services.engine.insights.types.InsightCandidate`
*structured facts only* (Story 7.2 turns them into O→E→E→A prose and formats currency).

Class names are 1:1 with FR-8.1's named patterns: no detector exists without a named
pattern, and vice versa. Each returns ``[]`` (never ``None``) when its pattern does not fire
or when there is too little history to be honest.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from services.engine.insights.config import (
    COLLISION_LOOKAHEAD_DAYS,
    COLLISION_MIN_BALANCE,
    MAX_EVIDENCE_POINTS,
    MIN_DATA_MONTHS_FOR_TREND,
    PACE_IMPROVED_MIN_PCT,
    PACE_RECENT_WINDOW_DAYS,
    POST_PAYDAY_SPIKE_MIN_PCT,
    POST_PAYDAY_WINDOW_DAYS,
    SMALL_PURCHASE_MAX_AMOUNT,
    SMALL_PURCHASE_MIN_COUNT,
    SMALL_PURCHASE_MIN_TOTAL,
    SUBSCRIPTION_AMOUNT_TOLERANCE_PCT,
    SUBSCRIPTION_ENDED_GRACE_DAYS,
    SUBSCRIPTION_MAX_GAP_DAYS,
    SUBSCRIPTION_MIN_GAP_DAYS,
    SUBSCRIPTION_MIN_OCCURRENCES,
    WEEKEND_PACE_MIN_RATIO,
    WEEKEND_PACE_MIN_WEEKEND_DAYS,
)
from services.engine.insights.protocol import InsightDetector
from services.engine.insights.types import (
    CommitmentRecord,
    EvidencePoint,
    InsightCandidate,
    InsightContext,
    TxnRecord,
)
from services.utils.enums import Criticality, Direction, Tone

_ZERO = Decimal("0")
_HUNDRED = Decimal("100")

# Order commitments most-critical first when picking an insight's severity.
_SEVERITY_ORDER: dict[str, int] = {"critical": 0, "important": 1, "flexible": 2}


# --------------------------------------------------------------------------------------
# Shared helpers (all ``_``-prefixed; pure functions over plain records).
# --------------------------------------------------------------------------------------
def _to_date(iso: str) -> date:
    return date.fromisoformat(iso)


def _debits(txns: tuple[TxnRecord, ...]) -> list[TxnRecord]:
    return [t for t in txns if t.direction == Direction.debit.value]


def _credits(txns: tuple[TxnRecord, ...]) -> list[TxnRecord]:
    return [t for t in txns if t.direction == Direction.credit.value]


def _merchant(t: TxnRecord) -> str:
    return t.merchant_normalized or t.description_raw or "Unknown"


def _has_merchant_identity(t: TxnRecord) -> bool:
    """False when a transaction carries no merchant signal at all (neither
    ``merchant_normalized`` nor ``description_raw``). Such rows must never be grouped
    with each other under a shared "Unknown" bucket — that would misreport unrelated
    debits as one recurring subscription."""
    return bool(t.merchant_normalized or t.description_raw.strip())


def data_months(txns: tuple[TxnRecord, ...]) -> int:
    """Calendar-month span of the history, inclusive (AC #9: "computed from the span of
    ctx.transactions" -- e.g. a January + June transaction pair spans 6 months, not the
    2 distinct months actually touched). Feeds FR-8.5."""
    if not txns:
        return 0
    dates = [_to_date(t.date) for t in txns]
    start, end = min(dates), max(dates)
    return (end.year - start.year) * 12 + (end.month - start.month) + 1


def _evidence(txns: list[TxnRecord], limit: int = MAX_EVIDENCE_POINTS) -> tuple[EvidencePoint, ...]:
    """The ``limit`` largest debits as exact evidence points (FR-8.2)."""
    top = sorted(txns, key=lambda t: t.amount, reverse=True)[:limit]
    return tuple(
        EvidencePoint(date=t.date, merchant=_merchant(t), amount=t.amount) for t in top
    )


def _sum(txns: list[TxnRecord]) -> Decimal:
    return sum((t.amount for t in txns), _ZERO)


def _infer_paydays(ctx: InsightContext) -> list[date]:
    """Detected paydays: ``ctx.income_dates`` if given, else inferred from credits.

    A salary is approximated as the largest *recurring* credit amount (seen >=2 times);
    a one-off transfer/refund that happens to exceed the real recurring salary is not
    mistaken for payday. When nothing recurs yet (a brand-new user's first month), the
    largest single credit is still the best honest guess. Returns ``[]`` when no income
    signal exists at all (detector then no-ops honestly).
    """
    if ctx.income_dates:
        return sorted(ctx.income_dates)
    credits = _credits(ctx.transactions)
    if not credits:
        return []
    by_amount: dict[Decimal, list[date]] = defaultdict(list)
    for c in credits:
        by_amount[c.amount].append(_to_date(c.date))
    payday_amount = max(by_amount)
    if len(by_amount[payday_amount]) == 1:
        recurring = {amt: dates for amt, dates in by_amount.items() if len(dates) >= 2}
        if recurring:
            payday_amount = max(recurring)
    return sorted(by_amount[payday_amount])


def _as_of(ctx: InsightContext) -> date | None:
    """The date to reason about "now" from.

    ``ctx.as_of`` when the caller supplied one (``load_insight_context`` always does). Falls
    back to the newest transaction date so a context built without ``as_of`` — every detector
    unit test predating this — still gets an honest "today" rather than silently treating a
    long-cancelled subscription as current. ``None`` only when there is no history at all.
    """
    if ctx.as_of is not None:
        return ctx.as_of
    if not ctx.transactions:
        return None
    return max(_to_date(t.date) for t in ctx.transactions)


@dataclass(frozen=True)
class _Series:
    """One merchant's near-fixed, ~monthly recurring charge run."""

    merchant: str
    charges: tuple[TxnRecord, ...]  # date-ascending
    monthly_amount: Decimal  # the median charge

    @property
    def last_charged(self) -> date:
        return _to_date(self.charges[-1].date)


def _recurring_series(txns: tuple[TxnRecord, ...]) -> list[_Series]:
    """Every merchant whose debits look like a fixed, ~monthly subscription.

    Shared by ``ZombieSubscriptionDetector`` (series still *live*) and
    ``SubscriptionEndedDetector`` (series that have *lapsed*) — one implementation of
    "what counts as a subscription", so the two can never disagree about it.
    """
    by_merchant: dict[str, list[TxnRecord]] = defaultdict(list)
    for d in _debits(txns):
        if not _has_merchant_identity(d):
            continue  # no merchant signal -- never group with unrelated debits
        by_merchant[_merchant(d)].append(d)

    out: list[_Series] = []
    for merchant, charges in by_merchant.items():
        if len(charges) < SUBSCRIPTION_MIN_OCCURRENCES:
            continue
        charges = sorted(charges, key=lambda t: t.date)
        amounts = sorted(c.amount for c in charges)
        mid = len(amounts) // 2
        median = amounts[mid] if len(amounts) % 2 else (amounts[mid - 1] + amounts[mid]) / 2
        if median <= _ZERO:
            continue
        tolerance = median * SUBSCRIPTION_AMOUNT_TOLERANCE_PCT / _HUNDRED
        if any(abs(a - median) > tolerance for a in amounts):
            continue  # amounts not near-equal → not a fixed subscription
        gaps = [
            (_to_date(charges[i + 1].date) - _to_date(charges[i].date)).days
            for i in range(len(charges) - 1)
        ]
        if not all(SUBSCRIPTION_MIN_GAP_DAYS <= g <= SUBSCRIPTION_MAX_GAP_DAYS for g in gaps):
            continue  # cadence isn't ~monthly
        out.append(
            _Series(merchant=merchant, charges=tuple(charges), monthly_amount=median)
        )
    return out


def _days_since_last_charge(series: _Series, as_of: date) -> int:
    return (as_of - series.last_charged).days


def _upcoming_commitments(ctx: InsightContext, as_of: date) -> list[CommitmentRecord]:
    """Commitments falling due inside the lookahead window, earliest first."""
    horizon = as_of + timedelta(days=COLLISION_LOOKAHEAD_DAYS)
    return sorted(
        (c for c in ctx.commitments if as_of <= c.due_date <= horizon),
        key=lambda c: c.due_date,
    )


def _project_balance(
    opening: Decimal, commitments: list[CommitmentRecord]
) -> list[tuple[CommitmentRecord, Decimal]]:
    """Debit each commitment from the opening balance in due-date order.

    Returns ``(commitment, running_balance_after_it)`` pairs. Shared by the collision
    detector (which reports the pairs that go *below* the floor) and the commitments-covered
    detector (which fires precisely when none of them do) — one projection, so the two can
    never disagree about whether a given week is safe.
    """
    running = opening
    out: list[tuple[CommitmentRecord, Decimal]] = []
    for commitment in commitments:
        running -= commitment.amount
        out.append((commitment, running))
    return out


def _latest_balance(txns: tuple[TxnRecord, ...]) -> Decimal | None:
    with_balance = [t for t in txns if t.balance_after is not None]
    if not with_balance:
        return None
    return max(with_balance, key=lambda t: t.date).balance_after


# --------------------------------------------------------------------------------------
# Detectors
# --------------------------------------------------------------------------------------
class PostPaydaySpikeDetector:
    """Spending rate in the days after payday runs well above the rest of the cycle."""

    pattern_name = "Post-payday spike"

    def detect(self, ctx: InsightContext) -> list[InsightCandidate]:
        debits = _debits(ctx.transactions)
        paydays = _infer_paydays(ctx)
        if not debits or not paydays:
            return []

        # Evaluate the most recent cycle -- a proactive insight should reflect current
        # behaviour, not stay anchored on month 1 forever. The baseline (``out_window``)
        # is scoped to *after* this cycle's window, so earlier cycles' own spikes never
        # pollute it (any date before this payday is, by construction, before window_end
        # too, since window_end = payday + a few days).
        payday = paydays[-1]
        window_end = payday + timedelta(days=POST_PAYDAY_WINDOW_DAYS)
        in_window = [d for d in debits if payday <= _to_date(d.date) <= window_end]
        out_window = [d for d in debits if _to_date(d.date) > window_end]
        if len(in_window) < 2 or not out_window:
            return []

        window_days = Decimal(POST_PAYDAY_WINDOW_DAYS + 1)  # inclusive of payday itself
        out_days = Decimal(len({d.date for d in out_window}) or 1)
        post_rate = _sum(in_window) / window_days
        base_rate = _sum(out_window) / out_days
        if base_rate <= _ZERO:
            return []

        spike_pct = (post_rate - base_rate) / base_rate * _HUNDRED
        if spike_pct < POST_PAYDAY_SPIKE_MIN_PCT:
            return []

        return [
            InsightCandidate(
                pattern_name=self.pattern_name,
                severity=Criticality.important.value,
                evidence=_evidence(in_window),
                metrics={
                    "spike_pct": spike_pct.quantize(Decimal("1")),
                    "post_payday_total": _sum(in_window),
                    "payday": payday.isoformat(),
                    "window_days": POST_PAYDAY_WINDOW_DAYS,
                },
                data_months=data_months(ctx.transactions),
            )
        ]


class DeathBySmallPurchasesDetector:
    """Many small debits quietly add up to a material total."""

    pattern_name = "Death by small purchases"

    def detect(self, ctx: InsightContext) -> list[InsightCandidate]:
        small = [d for d in _debits(ctx.transactions) if d.amount <= SMALL_PURCHASE_MAX_AMOUNT]
        total = _sum(small)
        if len(small) < SMALL_PURCHASE_MIN_COUNT or total < SMALL_PURCHASE_MIN_TOTAL:
            return []
        return [
            InsightCandidate(
                pattern_name=self.pattern_name,
                severity=Criticality.flexible.value,
                evidence=_evidence(small),
                metrics={
                    "count": len(small),
                    "total": total,
                    "max_amount": SMALL_PURCHASE_MAX_AMOUNT,
                },
                data_months=data_months(ctx.transactions),
            )
        ]


class ZombieSubscriptionDetector:
    """A near-fixed charge recurring at ~monthly cadence that is **still live**.

    The liveness check is load-bearing, not decoration: without it a subscription the user
    cancelled a year ago still satisfies "≥2 near-equal charges at monthly cadence" forever,
    and would be reported as an active drain on their money — a false insight, and (since
    ``SubscriptionEndedDetector`` reads the same series) one that would contradict the very
    next card in the feed. The grace window partitions the series set: live → here,
    lapsed → ``SubscriptionEndedDetector``. No series can be both.
    """

    pattern_name = "Zombie subscriptions"

    def detect(self, ctx: InsightContext) -> list[InsightCandidate]:
        as_of = _as_of(ctx)
        if as_of is None:
            return []

        out: list[InsightCandidate] = []
        for series in _recurring_series(ctx.transactions):
            if _days_since_last_charge(series, as_of) > SUBSCRIPTION_ENDED_GRACE_DAYS:
                continue  # lapsed, not live -- SubscriptionEndedDetector's business
            out.append(
                InsightCandidate(
                    pattern_name=self.pattern_name,
                    severity=Criticality.flexible.value,
                    evidence=_evidence(list(series.charges)),
                    metrics={
                        "merchant": series.merchant,
                        "monthly_amount": series.monthly_amount,
                        "occurrences": len(series.charges),
                    },
                    data_months=data_months(ctx.transactions),
                )
            )
        return out


class SubscriptionEndedDetector:
    """A recurring charge whose next payment never came — the user cancelled it. **A win.**

    The mirror image of ``ZombieSubscriptionDetector`` over the same recurring-series set,
    split by the same grace window, so exactly one of the two fires for any given merchant.
    """

    pattern_name = "Subscription ended"

    def detect(self, ctx: InsightContext) -> list[InsightCandidate]:
        as_of = _as_of(ctx)
        if as_of is None:
            return []

        out: list[InsightCandidate] = []
        for series in _recurring_series(ctx.transactions):
            days_since = _days_since_last_charge(series, as_of)
            if days_since <= SUBSCRIPTION_ENDED_GRACE_DAYS:
                continue  # still live -- ZombieSubscriptionDetector's business
            out.append(
                InsightCandidate(
                    pattern_name=self.pattern_name,
                    severity=Criticality.flexible.value,
                    tone=Tone.win.value,
                    evidence=_evidence(list(series.charges)),
                    metrics={
                        "merchant": series.merchant,
                        "monthly_amount": series.monthly_amount,
                        "last_charged": series.last_charged.isoformat(),
                        "days_since": days_since,
                    },
                    data_months=data_months(ctx.transactions),
                )
            )
        return out


class WeekendWeekdayPaceDetector:
    """Daily spend runs materially faster on weekends than on weekdays."""

    pattern_name = "Weekend vs weekday pace"

    def detect(self, ctx: InsightContext) -> list[InsightCandidate]:
        debits = _debits(ctx.transactions)
        if not debits:
            return []
        weekend = [d for d in debits if _to_date(d.date).weekday() >= 5]  # Sat=5, Sun=6
        weekday = [d for d in debits if _to_date(d.date).weekday() < 5]
        weekend_days = len({d.date for d in weekend})
        weekday_days = len({d.date for d in weekday})
        if weekend_days < WEEKEND_PACE_MIN_WEEKEND_DAYS or weekday_days == 0:
            return []

        weekend_rate = _sum(weekend) / Decimal(weekend_days)
        weekday_rate = _sum(weekday) / Decimal(weekday_days)
        if weekday_rate <= _ZERO:
            return []
        ratio = weekend_rate / weekday_rate
        if ratio < WEEKEND_PACE_MIN_RATIO:
            return []

        return [
            InsightCandidate(
                pattern_name=self.pattern_name,
                severity=Criticality.important.value,
                evidence=_evidence(weekend),
                metrics={
                    "weekend_daily": weekend_rate.quantize(Decimal("1")),
                    "weekday_daily": weekday_rate.quantize(Decimal("1")),
                    "ratio": ratio.quantize(Decimal("0.1")),
                },
                data_months=data_months(ctx.transactions),
            )
        ]


class UpcomingCommitmentCollisionDetector:
    """A commitment due soon would push the running balance below zero before payday."""

    pattern_name = "Upcoming commitment collision"

    def detect(self, ctx: InsightContext) -> list[InsightCandidate]:
        if not ctx.commitments or ctx.as_of is None:
            return []
        current_balance = _latest_balance(ctx.transactions)
        if current_balance is None:
            return []  # can't honestly project without a balance

        upcoming = _upcoming_commitments(ctx, ctx.as_of)
        projection = _project_balance(current_balance, upcoming)
        colliding = [pair for pair in projection if pair[1] < COLLISION_MIN_BALANCE]
        if not colliding:
            return []

        # Worst (lowest projected balance) first, so the evidence shown always includes
        # the commitment actually driving the cited shortfall -- not just whichever
        # commitments happen to be earliest-due when more than MAX_EVIDENCE_POINTS collide.
        colliding_by_severity = sorted(colliding, key=lambda pair: pair[1])
        worst = colliding_by_severity[0][1]

        # Always lead with the current-balance snapshot: a lone colliding commitment would
        # otherwise be a single evidence point, short of the documented 2-3 contract (AC #3).
        evidence = (
            EvidencePoint(
                date=ctx.as_of.isoformat(),
                merchant="Current balance",
                amount=current_balance,
            ),
            *(
                EvidencePoint(
                    date=commitment.due_date.isoformat(),
                    merchant=commitment.name,
                    amount=commitment.amount,
                )
                for commitment, _ in colliding_by_severity[: MAX_EVIDENCE_POINTS - 1]
            ),
        )
        severity = min(
            (commitment.criticality for commitment, _ in colliding),
            key=lambda s: _SEVERITY_ORDER.get(s, 1),
            default=Criticality.important.value,
        )
        return [
            InsightCandidate(
                pattern_name=self.pattern_name,
                severity=severity,
                evidence=evidence,
                metrics={
                    "current_balance": current_balance,
                    "projected_shortfall": -worst if worst < _ZERO else _ZERO,
                    "colliding_count": len(colliding),
                },
                data_months=data_months(ctx.transactions),
            )
        ]


class CommitmentsCoveredDetector:
    """Every bill due this week is already covered by the current balance. **A win.**

    The mirror image of ``UpcomingCommitmentCollisionDetector`` over the same projection —
    it fires precisely when that one does not. Requires at least one upcoming commitment:
    "all zero of your bills are covered" is not a win, it is a vacuous statement, and
    shipping it would teach the user that the win band is noise.
    """

    pattern_name = "Commitments covered"

    def detect(self, ctx: InsightContext) -> list[InsightCandidate]:
        if not ctx.commitments or ctx.as_of is None:
            return []
        current_balance = _latest_balance(ctx.transactions)
        if current_balance is None:
            return []  # can't honestly project without a balance

        upcoming = _upcoming_commitments(ctx, ctx.as_of)
        if not upcoming:
            return []  # nothing due -- no claim to make either way

        projection = _project_balance(current_balance, upcoming)
        if any(balance < COLLISION_MIN_BALANCE for _, balance in projection):
            return []  # a collision -- the other detector's business

        headroom = projection[-1][1]  # balance left after the last bill clears
        # Named ``due_total``, not ``total_due``: the narrator formats a Decimal as currency
        # by matching a *suffix* on its key, and "total" is a registered suffix while "due"
        # is not -- the latter would reach the model as a bare "2400.00" instead of "₹2,400".
        due_total = sum((c.amount for c in upcoming), _ZERO)

        # Lead with the balance doing the covering, then the bills it covers -- the same
        # evidence shape the collision detector uses, so the two read as one family.
        evidence = (
            EvidencePoint(
                date=ctx.as_of.isoformat(),
                merchant="Current balance",
                amount=current_balance,
            ),
            *(
                EvidencePoint(
                    date=c.due_date.isoformat(), merchant=c.name, amount=c.amount
                )
                for c in upcoming[: MAX_EVIDENCE_POINTS - 1]
            ),
        )
        return [
            InsightCandidate(
                pattern_name=self.pattern_name,
                severity=Criticality.flexible.value,
                tone=Tone.win.value,
                evidence=evidence,
                metrics={
                    "covered_count": len(upcoming),
                    "due_total": due_total,
                    "current_balance": current_balance,
                    "headroom": headroom,
                },
                data_months=data_months(ctx.transactions),
            )
        ]


class SpendingPaceImprovedDetector:
    """Recent daily spend is materially below the earlier baseline. **A win.**

    Deliberately silent on thin history (``MIN_DATA_MONTHS_FOR_TREND``): one quiet week is
    not a trend, and a congratulation the data cannot support is exactly the kind of
    dishonesty this product exists not to commit.

    Emits **no evidence points**. Every other detector's evidence is a list of transactions,
    but this pattern's claim is about a *rate*, and no single transaction is evidence for a
    rate — citing "your 3 biggest recent purchases" under a card that says you're spending
    less would argue against itself. The empty-evidence path renders the card without an
    evidence block (``insights.py::_evidence_block``), which is the honest outcome.
    """

    pattern_name = "Spending pace improved"

    def detect(self, ctx: InsightContext) -> list[InsightCandidate]:
        as_of = _as_of(ctx)
        if as_of is None:
            return []
        if data_months(ctx.transactions) < MIN_DATA_MONTHS_FOR_TREND:
            return []  # too little history to claim a trend honestly

        cutoff = as_of - timedelta(days=PACE_RECENT_WINDOW_DAYS)
        debits = _debits(ctx.transactions)
        recent = [d for d in debits if _to_date(d.date) > cutoff]
        baseline = [d for d in debits if _to_date(d.date) <= cutoff]
        if not baseline:
            return []

        baseline_start = min(_to_date(d.date) for d in baseline)
        baseline_days = (cutoff - baseline_start).days + 1
        if baseline_days < 1:
            return []

        baseline_rate = _sum(baseline) / baseline_days
        if baseline_rate <= _ZERO:
            return []
        recent_rate = _sum(recent) / PACE_RECENT_WINDOW_DAYS

        drop_pct = (baseline_rate - recent_rate) / baseline_rate * _HUNDRED
        if drop_pct < PACE_IMPROVED_MIN_PCT:
            return []

        return [
            InsightCandidate(
                pattern_name=self.pattern_name,
                severity=Criticality.flexible.value,
                tone=Tone.win.value,
                evidence=(),  # a rate has no transaction to cite -- see the class docstring
                metrics={
                    "drop_pct": drop_pct.quantize(Decimal("1")),
                    "recent_daily": recent_rate.quantize(Decimal("1")),
                    "baseline_daily": baseline_rate.quantize(Decimal("1")),
                    "monthly_saving": (
                        (baseline_rate - recent_rate) * PACE_RECENT_WINDOW_DAYS
                    ).quantize(Decimal("1")),
                    "window_days": PACE_RECENT_WINDOW_DAYS,
                },
                data_months=data_months(ctx.transactions),
            )
        ]


#: Every detector, warnings first (FR-8.1 order) then the wins. Typed as the protocol to
#: document the contract. The wins exist because a feed that can only ever deliver bad news
#: is structurally incapable of telling a user they improved (market research 2026-07-12).
ALL_DETECTORS: tuple[InsightDetector, ...] = (
    PostPaydaySpikeDetector(),
    DeathBySmallPurchasesDetector(),
    ZombieSubscriptionDetector(),
    WeekendWeekdayPaceDetector(),
    UpcomingCommitmentCollisionDetector(),
    SubscriptionEndedDetector(),
    CommitmentsCoveredDetector(),
    SpendingPaceImprovedDetector(),
)


def run_all_detectors(ctx: InsightContext) -> list[InsightCandidate]:
    """Run every detector in FR-8.1 order and concatenate their candidates."""
    candidates: list[InsightCandidate] = []
    for detector in ALL_DETECTORS:
        candidates.extend(detector.detect(ctx))
    return candidates
