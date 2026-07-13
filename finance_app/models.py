"""Database tables for the AI-Powered Personal Finance Analyzer (Story 1.2).

The 8 tables required by the AC:
``users`` · ``uploaded_files`` · ``transactions`` · ``merchant_rules`` ·
``commitments`` · ``score_events`` · ``insights`` · ``chat_messages``.

Design notes (see story 1-2 Dev Notes for the full rationale):

* **``users`` = reflex-local-auth's ``LocalUser``** (tablename ``localuser``). We do NOT
  hand-roll a second users table — that would fragment identity and break Story 1.3's
  auto-login. Importing ``reflex_local_auth`` here registers ``LocalUser`` (and its auth
  session table) with the shared SQLModel metadata so migrations create them. Every
  user-scoped table's ``user_id`` FK therefore targets ``localuser.id``.
* **Enums are stored as plain ``str`` columns** (no native DB enum), governed by the
  framework-agnostic ``services/utils/enums.py`` so ``services/`` never has to import this
  UI-layer module (AD-2). Defaults use the enum ``.value``.
* **Money is ``Decimal``**, never ``float`` (AD-8): ``amount``, ``balance_after``,
  ``commitments.amount``. ``float`` is display-only, confined to ``formatINR`` (AD-13).
* ``rx.Model`` supplies the integer ``id`` primary key automatically (AC #2); we only add
  the ``user_id`` FK and the domain columns.
* **``services/narrate/tools.py`` (Story 6.2) needs to query ``Transaction`` for the Copilot's
  read-only tools, but ``services/`` must never import ``finance_app`` (AD-2).** Resolved the
  same way ``services/ingestion/persist.py`` (Story 2.5) already resolved the identical
  problem: the model class is *injected* as a parameter (``txn_model: type``) by the caller
  (``finance_app/state/copilot_state.py`` passes this module's ``Transaction`` in), never
  imported by ``services/``. ``Transaction`` stays owned here, one definition, no relocation.
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import reflex as rx
import reflex_local_auth  # noqa: F401  — registers LocalUser (`localuser`) + auth session tables
import sqlmodel

from services.utils.enums import TONE_DEFAULT, CategorySource, Criticality

# reflex-local-auth's user table name — the FK target for every user-scoped table.
USER_FK = "localuser.id"


def _utcnow() -> datetime:
    """Current UTC instant as a **naive** datetime — the project-wide storage convention.

    Every timestamp column below is a naive SQLAlchemy ``DateTime``. Writing a tz-*aware* value
    into one stores the wall-clock and silently drops the offset, so what comes back on read is
    naive anyway — and comparing that naive value against an aware ``datetime.now(timezone.utc)``
    raises ``TypeError``. Returning naive UTC here makes the write side agree with the column,
    so a round-tripped timestamp compares cleanly without a shim.

    **The convention is: every stored timestamp is UTC, and naive.** Convert to aware only at
    the point of display or arithmetic against an aware value.
    (Flagged in the Story 1.2 review to be settled when timestamps were first consumed; the
    Epic 5 dashboard and Confidence-Score drill-in are that consumer.)
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


class UploadedFile(rx.Model, table=True):
    """A statement file a user uploaded (Epic 2 populates parse metadata)."""

    __tablename__ = "uploaded_files"

    user_id: int = sqlmodel.Field(foreign_key=USER_FK, index=True)
    filename: str
    status: str = "uploaded"  # uploaded | parsing | parsed | failed (Epic 2 refines)
    uploaded_at: datetime = sqlmodel.Field(default_factory=_utcnow)


class Transaction(rx.Model, table=True):
    """Canonical transaction row (AD-6). Every parser normalizes to this shape."""

    __tablename__ = "transactions"

    user_id: int = sqlmodel.Field(foreign_key=USER_FK, index=True)
    source_file_id: int | None = sqlmodel.Field(
        default=None, foreign_key="uploaded_files.id", index=True
    )
    date: str  # ISO 'YYYY-MM-DD' (normalized at ingestion — dedup key component)
    description_raw: str
    merchant_normalized: str | None = None
    amount: Decimal = sqlmodel.Field(max_digits=12, decimal_places=2)  # Decimal, not float (AD-8)
    direction: str  # Direction: 'credit' | 'debit'
    balance_after: Decimal | None = sqlmodel.Field(
        default=None, max_digits=12, decimal_places=2
    )
    category: str | None = None
    category_source: str | None = None  # CategorySource: 'rule' | 'llm' | 'user'
    category_confidence: float | None = None  # display/threshold only, never money math
    reasoning: str | None = None  # Tier-2 LLM's one-sentence rationale (Story 3.2); rule/user rows leave this None
    created_at: datetime = sqlmodel.Field(default_factory=_utcnow)


class MerchantRule(rx.Model, table=True):
    """User-taught categorization rule ("Teach Me", Story 3.3). Per-user, not global."""

    __tablename__ = "merchant_rules"

    user_id: int = sqlmodel.Field(foreign_key=USER_FK, index=True)
    pattern: str
    category: str
    source: str = CategorySource.user.value  # 'user'
    created_at: datetime = sqlmodel.Field(default_factory=_utcnow)


class Commitment(rx.Model, table=True):
    """A recurring obligation the engine ring-fences (Story 5.5 / FR-9)."""

    __tablename__ = "commitments"

    user_id: int = sqlmodel.Field(foreign_key=USER_FK, index=True)
    name: str
    amount: Decimal = sqlmodel.Field(max_digits=12, decimal_places=2)  # Decimal, not float
    due_day: int  # 1–31; 31 renders as "end of month" (Story 5.5)
    criticality: str = Criticality.important.value  # default 'important' (AC #3 / FR-4.3)
    created_at: datetime = sqlmodel.Field(default_factory=_utcnow)


class CommitmentSuggestion(rx.Model, table=True):
    """A recurring charge the detector proposed, and the user's decision on it (Story 5.6).

    Only *decided* signatures are stored — one row per pattern the user confirmed or dismissed.
    Pending candidates are recomputed from transactions on each page load, so this table holds
    just enough to guarantee a dismissed (or already-confirmed) pattern is never re-surfaced
    (FR-9.1). ``signature`` is the detector's stable ``"<merchant>@<due_day>"`` identity.
    """

    __tablename__ = "commitment_suggestions"

    user_id: int = sqlmodel.Field(foreign_key=USER_FK, index=True)
    signature: str = sqlmodel.Field(index=True)
    status: str  # 'confirmed' | 'dismissed'
    created_at: datetime = sqlmodel.Field(default_factory=_utcnow)


class ScoreEvent(rx.Model, table=True):
    """Auditable Confidence-Score change (AD-9). The UI score is the latest row here."""

    __tablename__ = "score_events"

    user_id: int = sqlmodel.Field(foreign_key=USER_FK, index=True)
    score: int
    delta: int
    trigger_event: str  # spelled trigger_event, NOT triggering_event (AD-9 / CS-3)
    explanation: str
    suggested_action: str | None = None
    timestamp: datetime = sqlmodel.Field(default_factory=_utcnow)


class Insight(rx.Model, table=True):
    """A proactive behavioral insight in Observation-Evidence-Explanation-Action shape (Epic 7).

    Story 7.3 adds 5 columns beyond the original Story 1.2 schema:
    ``effect`` (Story 7.2's third O-E-E-A sentence had no column before this),
    ``dismissed_at``, ``severity`` (drives Story 7.3's severity-tier ordering),
    ``metric_value`` (the ≥15%-materially-changed resurface comparison), and
    ``dedup_key`` (identity key for resurface/dedup lookups -- not displayed;
    equals ``pattern_name`` except for Zombie-subscription candidates, which are
    keyed per-merchant since one detector run can emit more than one).
    """

    __tablename__ = "insights"

    user_id: int = sqlmodel.Field(foreign_key=USER_FK, index=True)
    pattern_name: str
    observation: str
    evidence: str
    explanation: str
    effect: str
    action_suggestion: str
    status: str = "active"  # active | dismissed (dismiss lifecycle, FR-8.4)
    severity: str = Criticality.important.value  # 'critical' | 'important' | 'flexible'
    # 'watch' | 'win' -- orthogonal to severity (which answers "how urgent", and so cannot
    # express "this is good news"). Drives the Insights page's two bands.
    tone: str = TONE_DEFAULT.value
    metric_value: Decimal | None = sqlmodel.Field(default=None, max_digits=12, decimal_places=2)
    dedup_key: str
    dismissed_at: datetime | None = None
    created_at: datetime = sqlmodel.Field(default_factory=_utcnow)


class ChatMessage(rx.Model, table=True):
    """A Copilot chat turn, stored server-side and scoped to the user (Story 6.1 / FR-7.9)."""

    __tablename__ = "chat_messages"

    user_id: int = sqlmodel.Field(foreign_key=USER_FK, index=True)
    role: str  # 'user' | 'assistant'
    content: str
    trace_sources: str | None = None  # JSON-encoded citations (FR-7.5)
    timestamp: datetime = sqlmodel.Field(default_factory=_utcnow)
