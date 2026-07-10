"""Canonical transaction schema — the ingestion contract (AD-6, Story 2.1).

Every parser (CSV, PDF, future Account-Aggregator) normalizes its output to this one
shape *before* returning. No parser-specific row shape may cross the ``services/ingestion/``
boundary — downstream services (categorize, engine, narrate) read only this struct and
never fork on source format.

Why a framework-agnostic dataclass and not ``finance_app.models.Transaction``:
``services/`` must never import the UI/app layer (AD-2, enforced by
``tests/test_service_boundary.py``). The ``rx.Model`` in ``finance_app/models.py`` is the
*persistence* shape; this dataclass is the *ingestion* shape. The ``rx.State`` upload
handler is the single bridge that turns these parsed rows into DB rows (assigning
``user_id`` / ``source_file_id`` and letting the DB assign ``id`` / ``created_at``).

Field provenance (AD-6 lists all twelve canonical fields):

* **Known at parse time** (a parser must populate): ``date``, ``description_raw``,
  ``amount``, ``direction``, and — when the statement provides it — ``balance_after``
  and ``merchant_normalized``.
* **Assigned downstream** (default ``None`` here): ``user_id`` and ``source_file_id`` are
  set by the persistence layer; ``id`` and ``created_at`` are assigned by the DB;
  ``category`` / ``category_source`` / ``category_confidence`` are filled by Epic 3
  categorization. A fresh parse leaves them unset.

Invariants baked in:

* ``amount`` and ``balance_after`` are ``Decimal`` — never ``float`` (AD-8). ``float`` is
  display-only and confined to ``formatINR`` (AD-13).
* ``date`` is an ISO ``'YYYY-MM-DD'`` string, normalized by the parser — it is a component
  of the dedup key ``(user_id, date, amount, description_raw, balance_after)`` (Story 2.5).
* ``direction`` is the shared ``Direction`` enum (``credit`` | ``debit``) from
  ``services/utils/enums.py`` — the same source the DB column documents.
* The dataclass is **frozen**: a parsed row is an immutable value; downstream steps build
  new rows (via ``replace``) rather than mutating in place.
"""
from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from services.utils.enums import Direction

__all__ = ["Transaction"]


@dataclass(frozen=True, slots=True)
class Transaction:
    """One normalized transaction — the only shape that crosses ``services/ingestion/`` (AD-6)."""

    # --- Known at parse time -------------------------------------------------
    date: str  # ISO 'YYYY-MM-DD', normalized by the parser (dedup key component)
    description_raw: str
    amount: Decimal  # Decimal, never float (AD-8)
    direction: Direction  # 'credit' | 'debit'
    balance_after: Decimal | None = None
    merchant_normalized: str | None = None

    # --- Assigned downstream (unknown to a parser) ---------------------------
    category: str | None = None
    category_source: str | None = None  # CategorySource: 'rule' | 'llm' | 'user'
    category_confidence: float | None = None  # threshold/display only, never money math
    user_id: int | None = None  # set by the persistence layer
    source_file_id: int | None = None  # set by the persistence layer
    id: int | None = None  # assigned by the DB
    created_at: datetime | None = None  # assigned by the DB

    def __post_init__(self) -> None:
        # Fail loudly at construction rather than letting a float amount silently poison
        # engine arithmetic downstream (AD-8). Bools are ints in Python — reject them too.
        for name in ("amount", "balance_after"):
            value = getattr(self, name)
            if value is None:
                continue
            if not isinstance(value, Decimal):
                raise TypeError(
                    f"Transaction.{name} must be Decimal, not {type(value).__name__} "
                    f"(AD-8: no float in money math)"
                )
        if not isinstance(self.direction, Direction):
            raise TypeError(
                f"Transaction.direction must be a Direction enum, not "
                f"{type(self.direction).__name__} — parsers map source flags to "
                f"Direction.credit / Direction.debit (AD-6)"
            )

    def with_fields(self, **changes: object) -> "Transaction":
        """Return a copy with ``changes`` applied (the frozen-dataclass update idiom).

        Used by the persistence layer to stamp ``user_id`` / ``source_file_id`` and by
        Epic 3 to attach categorization, without mutating the immutable parsed row.
        """
        return dataclasses.replace(self, **changes)