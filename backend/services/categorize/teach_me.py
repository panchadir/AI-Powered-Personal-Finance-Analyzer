"""Teach Me — user-taught merchant rules (Story 3.3, FR-3.4).

Session-injected, model-injected (AD-2/AD-14 — mirrors ``services/ingestion/persist.py``):
these functions take a live sqlmodel ``Session`` and the caller's model classes, and never
construct their own session or import ``finance_app`` (``services/`` boundary).

Every function here is explicitly ``user_id``-scoped (AD-4). ``merchant_rules`` looks like
reference data but is per-user — project-context's own Agent-Misread Guards call this out by
name: leaking it cross-user is an IDOR.

Matching uses the same case-insensitive substring semantics as
``services/categorize/rules.py``'s ``_match`` (deliberately — "what will match on the next
upload" and "what gets updated right now" must agree), so ``reapply_correction`` filters in
Python rather than a SQL ``LIKE``/``ILIKE`` (which would need wildcard-escaping to match the
same semantics safely) — acceptable at this project's single-user local scale.

Code-review follow-up (2026-07-10): the upsert lookup and matching now agree on
case-insensitivity (both were case-insensitive at match time, but the upsert's own lookup
was accidentally case-sensitive, letting case variants of an already-taught pattern pile up
as duplicate rows). A blank/whitespace-only pattern is refused everywhere — ``_match`` in
``rules.py`` and the substring check below would otherwise treat an empty string as
contained in *every* description, silently recategorizing a user's entire history.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func
from sqlmodel import select

from services.utils.enums import CategorySource

__all__ = ["load_user_merchant_rules", "write_merchant_rule", "reapply_correction"]


def load_user_merchant_rules(session, merchant_rule_model: type, user_id: int) -> list[tuple[str, str]]:
    """This user's taught rules as ``(pattern, category)`` pairs, for
    ``services.categorize.rules.categorize_rules(..., user_rules=...)``.

    ``user_id``-scoped (AD-4) — never returns another user's taught rules. Ordered
    most-recently-taught first (``created_at`` desc, ``id`` desc as a same-instant
    tiebreaker) so, if two stored patterns both match the same description, ``_match``'s
    first-match-wins loop favors the rule the user taught more recently rather than an
    arbitrary DB row order.
    """
    rows = session.exec(
        select(merchant_rule_model)
        .where(merchant_rule_model.user_id == user_id)
        .order_by(merchant_rule_model.created_at.desc(), merchant_rule_model.id.desc())
    ).all()
    return [(row.pattern, row.category) for row in rows]


def write_merchant_rule(
    session, merchant_rule_model: type, user_id: int, pattern: str, category: str
) -> None:
    """Upsert: a second correction for the same ``(user_id, pattern)`` updates the existing
    rule's category (and refreshes ``created_at``, so it also wins the recency ordering
    above) rather than inserting a conflicting second row. The lookup is case-insensitive to
    match ``_match``'s/``reapply_correction``'s own case-insensitive semantics — otherwise a
    case-only variant of an already-taught pattern would insert a near-duplicate instead of
    updating it.

    A blank/whitespace-only ``pattern`` is silently refused (no-op): it would otherwise be a
    rule that matches every transaction.
    """
    if not pattern.strip():
        return
    existing = session.exec(
        select(merchant_rule_model).where(
            merchant_rule_model.user_id == user_id,
            func.lower(merchant_rule_model.pattern) == pattern.lower(),
        )
    ).one_or_none()
    if existing is not None:
        existing.category = category
        existing.created_at = datetime.now(timezone.utc)
        session.add(existing)
    else:
        session.add(
            merchant_rule_model(  # type: ignore[call-arg]
                user_id=user_id, pattern=pattern, category=category,
                source=CategorySource.user.value,
            )
        )
    session.commit()


def reapply_correction(session, txn_model: type, user_id: int, pattern: str, category: str) -> int:
    """Update every one of this user's transactions whose description case-insensitively
    contains ``pattern`` to ``category`` / ``category_source='user'`` / full confidence.

    ``user_id``-scoped (AD-4). Returns the count of rows updated. A blank/whitespace-only
    ``pattern`` matches nothing (returns 0) instead of matching every transaction.
    """
    needle = pattern.strip().lower()
    if not needle:
        return 0
    rows = session.exec(
        select(txn_model).where(txn_model.user_id == user_id)
    ).all()
    matched = [row for row in rows if needle in row.description_raw.lower()]
    for row in matched:
        row.category = category
        row.category_source = CategorySource.user.value
        row.category_confidence = 1.0
        session.add(row)
    session.commit()
    return len(matched)
