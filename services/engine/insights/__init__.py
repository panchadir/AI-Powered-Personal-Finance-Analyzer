"""Proactive-insight detector engine (Epic 7, Story 7.1).

Five deterministic, framework-agnostic detectors (FR-8.1) that turn a user's transaction
history into structured :class:`InsightCandidate` facts — **zero LLM calls** (AD-1), no
``reflex`` / ``finance_app`` imports (AD-2), all money in ``Decimal`` (AD-8).

Public API:

* Types: :class:`TxnRecord`, :class:`CommitmentRecord`, :class:`InsightContext`,
  :class:`EvidencePoint`, :class:`InsightCandidate`.
* Contract: :class:`InsightDetector` protocol.
* Detectors: the five FR-8.1 classes + :data:`ALL_DETECTORS` + :func:`run_all_detectors`.

The DB read and the mandatory ``user_id``-scoped query (AD-4) belong to the caller (a later
Epic 7 ``rx.State`` handler / repository), which maps rows → these plain records. Narration
into O→E→E→A prose is Story 7.2; persistence + dismiss lifecycle is Story 7.3.
"""
from services.engine.insights.config import (
    MAX_EVIDENCE_POINTS,
    MIN_DATA_MONTHS_FOOTNOTE,
)
from services.engine.insights.detectors import (
    ALL_DETECTORS,
    DeathBySmallPurchasesDetector,
    PostPaydaySpikeDetector,
    UpcomingCommitmentCollisionDetector,
    WeekendWeekdayPaceDetector,
    ZombieSubscriptionDetector,
    run_all_detectors,
)
from services.engine.insights.protocol import InsightDetector
from services.engine.insights.types import (
    CommitmentRecord,
    EvidencePoint,
    InsightCandidate,
    InsightContext,
    TxnRecord,
)

__all__ = [
    # types
    "TxnRecord",
    "CommitmentRecord",
    "InsightContext",
    "EvidencePoint",
    "InsightCandidate",
    # contract
    "InsightDetector",
    # detectors
    "PostPaydaySpikeDetector",
    "DeathBySmallPurchasesDetector",
    "ZombieSubscriptionDetector",
    "WeekendWeekdayPaceDetector",
    "UpcomingCommitmentCollisionDetector",
    "ALL_DETECTORS",
    "run_all_detectors",
    # config (re-exported for callers/narrator)
    "MAX_EVIDENCE_POINTS",
    "MIN_DATA_MONTHS_FOOTNOTE",
]
