"""Plain, framework-agnostic value types for the insight detector engine (Story 7.1).

These are the services-side inputs/outputs for ``services/engine/insights``. They import
nothing from ``reflex`` or ``finance_app`` (AD-2) — the caller (a later Epic 7 ``rx.State``
handler / repository) maps DB rows to :class:`TxnRecord` / :class:`CommitmentRecord` and
applies the mandatory ``user_id`` filter (AD-4). Detectors never touch a DB session.

All money is :class:`~decimal.Decimal`, never ``float`` (AD-8). Detectors emit *structured
facts only* — no prose, no pre-formatted currency; Story 7.2 narrates these into the
Observation-Evidence-Explanation-Action shape and applies ``formatINR``/``formatDate``.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from services.utils.enums import TONE_DEFAULT


@dataclass(frozen=True)
class TxnRecord:
    """The minimal transaction shape the detectors need — the services-side twin of the
    canonical ``finance_app.models.Transaction`` (imported by neither side; AD-2).

    ``date`` is an ISO ``YYYY-MM-DD`` string (matches ``Transaction.date``). When Epic 2's
    Story 2.1 formalizes the canonical services-side ``Transaction`` type, align to it —
    this is deliberately minimal so that alignment is cheap.
    """

    date: str
    amount: Decimal
    direction: str  # 'credit' | 'debit' (services.utils.enums.Direction values)
    description_raw: str = ""
    merchant_normalized: str | None = None
    category: str | None = None
    balance_after: Decimal | None = None


@dataclass(frozen=True)
class CommitmentRecord:
    """A recurring obligation for the collision detector. ``due_date`` is a concrete date
    (the caller resolves ``Commitment.due_day`` → a date, as Epic 4's engine does)."""

    name: str
    amount: Decimal
    due_date: date
    criticality: str = "important"  # 'critical' | 'important' | 'flexible'


@dataclass(frozen=True)
class InsightContext:
    """Everything the detectors read for one user. No DB / Reflex types (AD-2)."""

    transactions: tuple[TxnRecord, ...] = ()
    commitments: tuple[CommitmentRecord, ...] = ()
    as_of: date | None = None
    income_dates: tuple[date, ...] = ()  # detected paydays; may be empty


@dataclass(frozen=True)
class EvidencePoint:
    """One exact data point cited by an insight (FR-8.2: real date / merchant / amount)."""

    date: str  # ISO 'YYYY-MM-DD'
    merchant: str
    amount: Decimal


@dataclass(frozen=True)
class InsightCandidate:
    """A detected pattern as structured facts — never prose (AD-1 / FR-8.2).

    ``metrics`` carries every figure a narrator (Story 7.2) will cite verbatim, so the
    narrator performs *no* arithmetic. ``severity`` uses ``Criticality`` values so Story
    7.3 can order newest-first within a severity tier. ``data_months`` feeds FR-8.5's
    "More data sharpens these patterns" footnote (rendered later, in Story 7.3).
    """

    pattern_name: str
    severity: str  # 'critical' | 'important' | 'flexible'
    evidence: tuple[EvidencePoint, ...] = ()
    # compare=False: metrics is a plain dict (unhashable) -- excluding it from the
    # generated __eq__/__hash__ keeps InsightCandidate usable in sets/dict keys (Story 7.3).
    metrics: Mapping[str, object] = field(default_factory=dict, compare=False)
    data_months: int = 0
    #: ``watch`` (a pattern worth attention) or ``win`` (something going right). Orthogonal
    #: to ``severity`` -- see ``services.utils.enums.Tone``. Defaults to ``watch`` so the five
    #: original FR-8.1 detectors need no change.
    tone: str = TONE_DEFAULT.value
