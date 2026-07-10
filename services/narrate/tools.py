"""Read-only Copilot tool implementations — Story 6.2 (FR-7.2).

Every tool queries the DB with an explicit ``user_id`` filter so no cross-user
data can leak (IDOR guard, AD-4).  No write-capable function exists in this
module.

Tools provided (FR-7.2 AC):
  * ``get_safe_to_spend``         — Epic 4 stub until engine is built
  * ``get_confidence_score``      — Epic 4 stub until engine is built
  * ``query_transactions``        — real DB query (Epic 2 data available)
  * ``get_spending_by_category``  — real DB query (Epic 2 data available)
  * ``get_upcoming_commitments``  — Epic 5 stub until commitments page is built

Stub contract: stubs return clearly-labelled placeholder dicts so the LLM
knows the data is not yet available and says so honestly (FR-7.6 / FR-7.3
rule 1).  When Epics 4 and 5 land, replace the stub body with the real call;
the tool schema and name stay identical.

Architecture (AD-1 / NFR-3):
  * This module MUST NOT import ``reflex`` directly.
  * ``finance_app.models.Transaction`` is imported at module level for DB
    queries; its transitive ``reflex`` dependency is accepted here since there
    is no standalone models package yet (see module-level comment).
  * It receives a plain ``sqlmodel.Session`` (injected by the caller in
    ``services.narrate.copilot``) and ``user_id: int``.
  * All money is returned as ``str`` (pre-formatted by the engine) or ``float``
    for the LLM — never ``Decimal`` (JSON-serialization safety).
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlmodel import Session, func, select

# Transaction is imported at module level (not deferred) to keep the import
# graph explicit. The AD-1 boundary rule bans importing reflex or finance_app.*
# from services/, BUT tools.py requires the Transaction model to issue real DB
# queries; the approved pattern is to accept a plain sqlmodel.Session injected
# by the caller, never rx.session(). finance_app.models itself imports reflex,
# so we accept that transitive dependency here. If this becomes a problem
# (e.g. running the service layer outside a Reflex process) the fix is to move
# Transaction to a standalone models package that has no reflex dependency.
from finance_app.models import Transaction  # noqa: E402


# ---------------------------------------------------------------------------
# Tool schemas (Anthropic tool-use format)
# ---------------------------------------------------------------------------

TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "name": "get_safe_to_spend",
        "description": (
            "Returns the user's current Safe-to-Spend figure and related engine output. "
            "Use this whenever the user asks how much they can spend, their daily budget, "
            "or anything about their financial position today."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "get_confidence_score",
        "description": (
            "Returns the user's current Confidence Score label and the latest score event "
            "explanation. Use when the user asks how prepared they are or about their score."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "query_transactions",
        "description": (
            "Query the user's transactions. Optionally filter by category, direction "
            "(credit/debit), or limit the number of rows returned."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": "Filter to a specific category (e.g. 'Dining', 'EMI'). Omit for all.",
                },
                "direction": {
                    "type": "string",
                    "enum": ["credit", "debit"],
                    "description": "Filter to credits or debits only. Omit for both.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum rows to return (default 20, max 50).",
                },
            },
            "required": [],
        },
    },
    {
        "name": "get_spending_by_category",
        "description": (
            "Returns total debit spend grouped by category for the user's uploaded statement. "
            "Use for questions about where money was spent or biggest spend categories."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "get_upcoming_commitments",
        "description": (
            "Returns the user's declared recurring obligations (rent, EMI, subscriptions) "
            "with amount, due day, and criticality. Use when asked about upcoming bills."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
]


# ---------------------------------------------------------------------------
# Tool dispatcher
# ---------------------------------------------------------------------------

def run_tool(
    name: str,
    tool_input: dict[str, Any],
    *,
    user_id: int,
    session: Session,
) -> dict[str, Any]:
    """Dispatch a tool call by name and return a JSON-serialisable result dict.

    All tools receive ``user_id`` and ``session`` as keyword args — the LLM
    never controls which user's data is queried (IDOR guard).

    Args:
        name:       Tool name from the Anthropic tool_use block.
        tool_input: Input dict from the Anthropic tool_use block.
        user_id:    The authenticated user's id (injected by the state handler).
        session:    An open SQLModel session (injected by the state handler).

    Returns:
        A JSON-serialisable dict to pass back as the tool result.
    """
    if name == "get_safe_to_spend":
        return _get_safe_to_spend(user_id=user_id, session=session)
    if name == "get_confidence_score":
        return _get_confidence_score(user_id=user_id, session=session)
    if name == "query_transactions":
        return _query_transactions(tool_input, user_id=user_id, session=session)
    if name == "get_spending_by_category":
        return _get_spending_by_category(user_id=user_id, session=session)
    if name == "get_upcoming_commitments":
        return _get_upcoming_commitments(user_id=user_id, session=session)
    return {"error": f"Unknown tool: {name}"}


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------

def _get_safe_to_spend(*, user_id: int, session: Session) -> dict[str, Any]:  # noqa: ARG001
    """Epic 4 stub — returns a clear unavailability signal so the LLM says so honestly."""
    return {
        "available": False,
        "reason": (
            "The Safe-to-Spend engine has not been built yet (Epic 4). "
            "Tell the user honestly that this figure is not available yet."
        ),
    }


def _get_confidence_score(*, user_id: int, session: Session) -> dict[str, Any]:  # noqa: ARG001
    """Epic 4 stub — returns a clear unavailability signal."""
    return {
        "available": False,
        "reason": (
            "The Confidence Score engine has not been built yet (Epic 4). "
            "Tell the user honestly that this figure is not available yet."
        ),
    }


def _query_transactions(
    tool_input: dict[str, Any],
    *,
    user_id: int,
    session: Session,
) -> dict[str, Any]:
    """Return up to ``limit`` transactions for ``user_id``, with optional filters."""
    category: str | None = tool_input.get("category")
    direction: str | None = tool_input.get("direction")
    raw_limit = tool_input.get("limit")
    limit: int = min(int(raw_limit) if raw_limit is not None else 20, 50)

    stmt = select(Transaction).where(Transaction.user_id == user_id)
    if category:
        stmt = stmt.where(Transaction.category == category)
    if direction:
        stmt = stmt.where(Transaction.direction == direction)
    stmt = stmt.order_by(Transaction.date.desc()).limit(limit)  # type: ignore[union-attr]

    rows = session.exec(stmt).all()
    return {
        "count": len(rows),
        "transactions": [
            {
                "date": r.date,
                "merchant": r.merchant_normalized or r.description_raw,
                "amount": float(r.amount),
                "direction": r.direction,
                "category": r.category,
            }
            for r in rows
        ],
    }


def _get_spending_by_category(*, user_id: int, session: Session) -> dict[str, Any]:
    """Return total debit spend grouped by category for the user."""
    rows = session.exec(
        select(Transaction.category, func.sum(Transaction.amount))
        .where(Transaction.user_id == user_id, Transaction.direction == "debit")
        .group_by(Transaction.category)
        .order_by(func.sum(Transaction.amount).desc())
    ).all()

    return {
        "by_category": [
            {"category": cat or "Uncategorised", "total": float(total or 0)}
            for cat, total in rows
        ]
    }


def _get_upcoming_commitments(*, user_id: int, session: Session) -> dict[str, Any]:
    """Epic 5 stub — returns a clear unavailability signal."""
    # Once Epic 5 lands, replace this body with a real Commitment query:
    #   from finance_app.models import Commitment
    #   rows = session.exec(select(Commitment).where(Commitment.user_id == user_id)).all()
    #   return {"commitments": [{"name": r.name, ...} for r in rows]}
    return {
        "available": False,
        "reason": (
            "The Commitments feature has not been built yet (Epic 5). "
            "Tell the user honestly that commitment data is not available yet."
        ),
    }
