"""Deduplicated persistence of parsed transactions (Story 2.5, AD-6 dedup seam / AD-4).

A re-uploaded or overlapping statement must never create duplicate rows. Dedup is decided on
the canonical key ``(user_id, date, amount, description_raw, balance_after)`` — normalized
before comparison (ISO date, whitespace-collapsed description, ``abs(amount)``) by
:func:`~services.ingestion.normalize.dedup_key` — so CSV and PDF parsers and this insert path
can never disagree on "same transaction".

Two layers, both framework-agnostic:

* :func:`filter_new_transactions` — pure: given the already-stored keys, return the subset of
  parsed transactions that are genuinely new (also collapsing duplicates *within* the batch).
* :func:`persist_transactions` — the DB round-trip: reads this user's existing keys, filters,
  stamps ``user_id`` / ``source_file_id``, inserts, and reports counts.

The transaction **model** is *injected* (``txn_model``), not imported: ``services/`` must never
import ``finance_app`` (AD-2). The ``rx.State`` upload handler passes ``finance_app.models``'s
``Transaction`` + an ``rx.session()``; tests pass the same model on an in-memory SQLite engine
(AD-14 — sqlmodel data access, no Reflex app needed). Every read is ``user_id``-scoped (AD-4).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from sqlmodel import select

from services.ingestion.normalize import dedup_key
from services.ingestion.schema import Transaction
from services.utils.enums import Direction

__all__ = ["PersistResult", "filter_new_transactions", "persist_transactions"]


@dataclass(frozen=True)
class PersistResult:
    """Outcome of a persist call: how many rows were newly inserted vs skipped as duplicates."""

    inserted: int
    skipped: int


def filter_new_transactions(
    transactions: Iterable[Transaction], existing_keys: set
) -> list[Transaction]:
    """Return the transactions whose dedup key is not already present, first-seen order.

    Also collapses duplicates *within* ``transactions`` (a statement can list the same row
    twice), so a batch never inserts a duplicate of itself. Pure — no DB, fully unit-testable.
    """
    seen: set = set(existing_keys)
    new: list[Transaction] = []
    for txn in transactions:
        key = dedup_key(txn)
        if key in seen:
            continue
        seen.add(key)
        new.append(txn)
    return new


def _direction_value(direction: Any) -> str:
    """The stored string for a direction (the DB column is a plain ``str``)."""
    return direction.value if isinstance(direction, Direction) else str(direction)


def _to_model(txn_model: type, txn: Transaction):
    """Build a persistence-model row from a canonical parsed transaction."""
    return txn_model(
        user_id=txn.user_id,
        source_file_id=txn.source_file_id,
        date=txn.date,
        description_raw=txn.description_raw,
        merchant_normalized=txn.merchant_normalized,
        amount=txn.amount,
        direction=_direction_value(txn.direction),
        balance_after=txn.balance_after,
        category=txn.category,
        category_source=txn.category_source,
        category_confidence=txn.category_confidence,
    )


def persist_transactions(
    session,
    txn_model: type,
    user_id: int,
    source_file_id: int | None,
    transactions: Iterable[Transaction],
) -> PersistResult:
    """Insert only the genuinely-new transactions for ``user_id``; skip duplicates.

    ``session`` is a live sqlmodel ``Session``; ``txn_model`` is the injected transaction table
    class (``finance_app.models.Transaction``). Reads are scoped to ``user_id`` (AD-4), so one
    user's rows never dedup against — or leak into — another's.
    """
    stamped = [
        t.with_fields(user_id=user_id, source_file_id=source_file_id) for t in transactions
    ]
    # Existing keys for THIS user only (AD-4): a re-upload dedups against prior rows.
    existing_rows = session.exec(
        select(txn_model).where(txn_model.user_id == user_id)
    ).all()
    existing_keys = {dedup_key(row) for row in existing_rows}

    new = filter_new_transactions(stamped, existing_keys)
    for txn in new:
        session.add(_to_model(txn_model, txn))
    session.commit()
    return PersistResult(inserted=len(new), skipped=len(stamped) - len(new))