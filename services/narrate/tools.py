"""Read-only Copilot tool contract — Story 6.2 (FR-7.2).

This module is the *framework-agnostic* half of the Copilot tools: the Anthropic tool schemas
and a dispatcher. It holds **no** database or ``finance_app`` import (AD-2) — the actual reads
are performed by a :class:`CopilotData` provider injected by the caller (the ``rx.State``
handler, via ``finance_app.state.copilot_data``). That keeps the honesty-critical rule intact
— every tool is read-only and ``user_id``-scoped — while respecting the one-way UI → Service →
Data dependency direction: the service defines *what* the tools are; the UI layer supplies
*how* the data is fetched.

Tools provided (FR-7.2 AC), all read-only, no write path exists:
  * ``get_safe_to_spend``         — the engine's Safe-to-Spend figure (Epic 4)
  * ``get_confidence_score``      — the Confidence Score *label* (never the raw number, FR-5.5)
  * ``query_transactions``        — the user's transactions, optionally filtered
  * ``get_spending_by_category``  — debit spend grouped by category
  * ``get_upcoming_commitments``  — declared recurring obligations (Epic 5)

A provider method returns a JSON-serialisable dict. When a figure is genuinely unavailable
(e.g. no statement uploaded yet) the provider returns ``{"available": False, "reason": …}`` so
the LLM tells the user honestly rather than inventing a number (FR-7.3 rule 1 / FR-7.6).
"""
from __future__ import annotations

from typing import Any, Protocol


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


class CopilotData(Protocol):
    """The read-only data the Copilot tools need. Implemented in the UI/data layer.

    Every method is a read scoped to a single authenticated user (the provider binds the
    ``user_id`` at construction, so the LLM can never choose whose data is queried — the IDOR
    guard, AD-4). Each returns a JSON-serialisable dict.
    """

    def get_safe_to_spend(self) -> dict[str, Any]: ...

    def get_confidence_score(self) -> dict[str, Any]: ...

    def query_transactions(
        self, *, category: str | None, direction: str | None, limit: int | None
    ) -> dict[str, Any]: ...

    def get_spending_by_category(self) -> dict[str, Any]: ...

    def get_upcoming_commitments(self) -> dict[str, Any]: ...


def run_tool(name: str, tool_input: dict[str, Any], *, data: CopilotData) -> dict[str, Any]:
    """Dispatch a tool call by name to the injected provider. No DB access lives here.

    Args:
        name:       Tool name from the Anthropic ``tool_use`` block.
        tool_input: Input dict from the ``tool_use`` block.
        data:       The user-scoped, read-only data provider (injected by the caller).

    Returns:
        A JSON-serialisable dict to pass back as the tool result.
    """
    if name == "get_safe_to_spend":
        return data.get_safe_to_spend()
    if name == "get_confidence_score":
        return data.get_confidence_score()
    if name == "query_transactions":
        return data.query_transactions(
            category=tool_input.get("category"),
            direction=tool_input.get("direction"),
            limit=tool_input.get("limit"),
        )
    if name == "get_spending_by_category":
        return data.get_spending_by_category()
    if name == "get_upcoming_commitments":
        return data.get_upcoming_commitments()
    return {"error": f"Unknown tool: {name}"}
