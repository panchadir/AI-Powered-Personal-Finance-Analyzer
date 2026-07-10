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
from datetime import date, timedelta
from decimal import Decimal

from services.engine.insights.config import (
    COLLISION_LOOKAHEAD_DAYS,
    COLLISION_MIN_BALANCE,
    MAX_EVIDENCE_POINTS,
    POST_PAYDAY_SPIKE_MIN_PCT,
    POST_PAYDAY_WINDOW_DAYS,
    SMALL_PURCHASE_MAX_AMOUNT,
    SMALL_PURCHASE_MIN_COUNT,
    SMALL_PURCHASE_MIN_TOTAL,
    SUBSCRIPTION_AMOUNT_TOLERANCE_PCT,
    SUBSCRIPTION_MAX_GAP_DAYS,
    SUBSCRIPTION_MIN_GAP_DAYS,
    SUBSCRIPTION_MIN_OCCURRENCES,
    WEEKEND_PACE_MIN_RATIO,
)
from services.engine.insights.protocol import InsightDetector
from services.engine.insights.types import (
    EvidencePoint,
    InsightCandidate,
    InsightContext,
    TxnRecord,
)
from services.utils.enums import Criticality, Direction

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


def _data_months(txns: tuple[TxnRecord, ...]) -> int:
    """Distinct calendar months present in the history (feeds FR-8.5)."""
    return len({(_to_date(t.date).year, _to_date(t.date).month) for t in txns})


def _evidence(txns: list[TxnRecord], limit: int = MAX_EVIDENCE_POINTS) -> tuple[EvidencePoint, ...]:
    """The ``limit`` largest debits as exact evidence points (FR-8.2)."""
    top = sorted(txns, key=lambda t: t.amount, reverse=True)[:limit]
    return tuple(
        EvidencePoint(date=t.date, merchant=_merchant(t), amount=t.amount) for t in top
    )


def _sum(txns: list[TxnRecord]) -> Decimal:
    return sum((t.amount for t in txns), _ZERO)


def _infer_paydays(ctx: InsightContext) -> list[date]:
    """Detected paydays: ``ctx.income_dates`` if given, else the largest-credit dates.

    A salary is approximated as the largest credit; every credit at that amount is a
    payday. Returns ``[]`` when no income signal exists (detector then no-ops honestly).
    """
    if ctx.income_dates:
        return sorted(ctx.income_dates)
    credits = _credits(ctx.transactions)
    if not credits:
        return []
    max_credit = max(c.amount for c in credits)
    return sorted(_to_date(c.date) for c in credits if c.amount == max_credit)


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

        payday = paydays[0]
        window_end = payday + timedelta(days=POST_PAYDAY_WINDOW_DAYS)
        in_window = [d for d in debits if payday <= _to_date(d.date) <= window_end]
        out_window = [d for d in debits if not (payday <= _to_date(d.date) <= window_end)]
        if not in_window or not out_window:
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
                data_months=_data_months(ctx.transactions),
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
                data_months=_data_months(ctx.transactions),
            )
        ]


class ZombieSubscriptionDetector:
    """A near-fixed charge recurs at ~monthly cadence — a live (zombie) subscription."""

    pattern_name = "Zombie subscriptions"

    def detect(self, ctx: InsightContext) -> list[InsightCandidate]:
        by_merchant: dict[str, list[TxnRecord]] = defaultdict(list)
        for d in _debits(ctx.transactions):
            by_merchant[_merchant(d)].append(d)

        out: list[InsightCandidate] = []
        for merchant, charges in by_merchant.items():
            if len(charges) < SUBSCRIPTION_MIN_OCCURRENCES:
                continue
            charges = sorted(charges, key=lambda t: t.date)
            amounts = [c.amount for c in charges]
            median = sorted(amounts)[len(amounts) // 2]
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
                InsightCandidate(
                    pattern_name=self.pattern_name,
                    severity=Criticality.flexible.value,
                    evidence=_evidence(charges),
                    metrics={
                        "merchant": merchant,
                        "monthly_amount": median,
                        "occurrences": len(charges),
                    },
                    data_months=_data_months(ctx.transactions),
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
        if weekend_days == 0 or weekday_days == 0:
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
                data_months=_data_months(ctx.transactions),
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

        horizon = ctx.as_of + timedelta(days=COLLISION_LOOKAHEAD_DAYS)
        upcoming = sorted(
            (c for c in ctx.commitments if ctx.as_of <= c.due_date <= horizon),
            key=lambda c: c.due_date,
        )

        running = current_balance
        colliding = []
        for commitment in upcoming:
            running -= commitment.amount
            if running < COLLISION_MIN_BALANCE:
                colliding.append((commitment, running))
        if not colliding:
            return []

        evidence = tuple(
            EvidencePoint(
                date=commitment.due_date.isoformat(),
                merchant=commitment.name,
                amount=commitment.amount,
            )
            for commitment, _ in colliding[:MAX_EVIDENCE_POINTS]
        )
        worst = min(balance for _, balance in colliding)
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
                data_months=_data_months(ctx.transactions),
            )
        ]


#: The five detectors in FR-8.1 order. Typed as the protocol to document the contract.
ALL_DETECTORS: tuple[InsightDetector, ...] = (
    PostPaydaySpikeDetector(),
    DeathBySmallPurchasesDetector(),
    ZombieSubscriptionDetector(),
    WeekendWeekdayPaceDetector(),
    UpcomingCommitmentCollisionDetector(),
)


def run_all_detectors(ctx: InsightContext) -> list[InsightCandidate]:
    """Run every detector in FR-8.1 order and concatenate their candidates."""
    candidates: list[InsightCandidate] = []
    for detector in ALL_DETECTORS:
        candidates.extend(detector.detect(ctx))
    return candidates
