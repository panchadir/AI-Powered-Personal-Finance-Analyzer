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
  * ``get_spending_trend``        — debit spend per month, optionally one category (time trend)
  * ``get_insights``              — active behavioral insights the app already surfaced (Epic 7)
  * ``get_score_history``         — recent Confidence-Score changes (labels only, FR-5.5)
  * ``get_detected_subscriptions``— recurring charges the detector proposed but the user hasn't
                                    yet confirmed/dismissed (the "forgotten subscription" win)
  * ``get_income_summary``        — the next detected salary credit (date, amount, confidence)
  * ``get_data_coverage``         — how much statement data exists and whether it is stale

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
    {
        "name": "get_spending_trend",
        "description": (
            "Returns total debit spend for each calendar month, oldest month first. "
            "Use for questions comparing periods or asking whether spending is going up or "
            "down over time (e.g. 'am I spending more than last month?', 'is my dining "
            "increasing?'). Optionally scope the trend to a single category."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": "Limit the trend to one category (e.g. 'Dining'). Omit for all spend.",
                },
            },
            "required": [],
        },
    },
    {
        "name": "get_insights",
        "description": (
            "Returns the active behavioral insights the app has already detected for the user "
            "(each as observation, evidence, explanation, effect, and a suggested action). "
            "Use when the user asks what they should watch out for, what's noteworthy, or for "
            "warnings and things to improve. These are pre-computed — never invent new ones."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "get_score_history",
        "description": (
            "Returns the user's recent Confidence-Score changes, newest first — each with the "
            "score label, the direction of change (improved/dropped/unchanged), when it "
            "happened, and the explanation. Use when asked whether their score is improving, "
            "why it changed, or about their progress over time. Never exposes the raw number."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of recent changes to return (default 5, max 20).",
                },
            },
            "required": [],
        },
    },
    {
        "name": "get_detected_subscriptions",
        "description": (
            "Returns recurring charges the app detected in the user's transactions that they "
            "have NOT yet confirmed or dismissed — likely subscriptions or EMIs they may have "
            "forgotten. Each has the merchant, typical amount, due day, and how many times it "
            "was seen. Use when asked about subscriptions, recurring payments, or 'what am I "
            "paying for regularly'. These are suggestions to review, not confirmed commitments."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "get_income_summary",
        "description": (
            "Returns the user's next detected salary/income: expected date, amount, and a "
            "detection confidence (Low/Medium/High). Use when asked when they next get paid, "
            "their expected salary, or about their income. If no salary-shaped credit is found, "
            "reports that income is not detected — never guesses an amount."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "get_data_coverage",
        "description": (
            "Returns how much data the app has for the user: number of statements uploaded, "
            "transaction count, the date range covered, the statement's end date, and whether "
            "that data is stale (older than 30 days). Use when asked how much data you have, "
            "how current it is, or to honestly qualify an answer's reliability."
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

    def get_spending_trend(self, *, category: str | None) -> dict[str, Any]: ...

    def get_insights(self) -> dict[str, Any]: ...

    def get_score_history(self, *, limit: int | None) -> dict[str, Any]: ...

    def get_detected_subscriptions(self) -> dict[str, Any]: ...

    def get_income_summary(self) -> dict[str, Any]: ...

    def get_data_coverage(self) -> dict[str, Any]: ...


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
    if name == "get_spending_trend":
        return data.get_spending_trend(category=tool_input.get("category"))
    if name == "get_insights":
        return data.get_insights()
    if name == "get_score_history":
        return data.get_score_history(limit=tool_input.get("limit"))
    if name == "get_detected_subscriptions":
        return data.get_detected_subscriptions()
    if name == "get_income_summary":
        return data.get_income_summary()
    if name == "get_data_coverage":
        return data.get_data_coverage()
    return {"error": f"Unknown tool: {name}"}
