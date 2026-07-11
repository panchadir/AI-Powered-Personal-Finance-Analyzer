"""Unit suite for the Copilot tool dispatcher (Story 6.2, services/narrate/tools.py).

Verifies ``run_tool`` routes each tool name to the injected :class:`CopilotData` provider and
threads ``query_transactions`` filters through — using a fake provider, so this stays pure
(no DB, no ``finance_app`` import) and keeps ``tools.py`` on the right side of the AD-2
boundary it now respects.
"""
from __future__ import annotations

from typing import Any

from services.narrate.tools import TOOL_SCHEMAS, run_tool


class FakeData:
    """Records calls and returns sentinel dicts so dispatch is observable."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    def get_safe_to_spend(self) -> dict[str, Any]:
        self.calls.append(("get_safe_to_spend", {}))
        return {"available": True, "safe_to_spend_today": "₹1,250"}

    def get_confidence_score(self) -> dict[str, Any]:
        self.calls.append(("get_confidence_score", {}))
        return {"available": True, "label": "On track"}

    def query_transactions(self, *, category, direction, limit) -> dict[str, Any]:
        self.calls.append(("query_transactions", {"category": category, "direction": direction, "limit": limit}))
        return {"count": 0, "transactions": []}

    def get_spending_by_category(self) -> dict[str, Any]:
        self.calls.append(("get_spending_by_category", {}))
        return {"by_category": []}

    def get_upcoming_commitments(self) -> dict[str, Any]:
        self.calls.append(("get_upcoming_commitments", {}))
        return {"commitments": []}


def test_each_tool_routes_to_its_provider_method() -> None:
    data = FakeData()
    assert run_tool("get_safe_to_spend", {}, data=data)["safe_to_spend_today"] == "₹1,250"
    assert run_tool("get_confidence_score", {}, data=data)["label"] == "On track"
    assert run_tool("get_spending_by_category", {}, data=data) == {"by_category": []}
    assert run_tool("get_upcoming_commitments", {}, data=data) == {"commitments": []}

    called = [name for name, _ in data.calls]
    assert called == [
        "get_safe_to_spend",
        "get_confidence_score",
        "get_spending_by_category",
        "get_upcoming_commitments",
    ]


def test_query_transactions_threads_filters() -> None:
    data = FakeData()
    run_tool(
        "query_transactions",
        {"category": "Dining", "direction": "debit", "limit": 5},
        data=data,
    )
    assert data.calls[-1] == (
        "query_transactions",
        {"category": "Dining", "direction": "debit", "limit": 5},
    )


def test_query_transactions_defaults_missing_filters_to_none() -> None:
    data = FakeData()
    run_tool("query_transactions", {}, data=data)
    assert data.calls[-1][1] == {"category": None, "direction": None, "limit": None}


def test_unknown_tool_returns_error_not_raise() -> None:
    result = run_tool("delete_everything", {}, data=FakeData())
    assert "error" in result


def test_tool_schemas_match_provider_methods() -> None:
    # Every advertised tool name must be a method the provider protocol exposes.
    schema_names = {t["name"] for t in TOOL_SCHEMAS}
    assert schema_names == {
        "get_safe_to_spend",
        "get_confidence_score",
        "query_transactions",
        "get_spending_by_category",
        "get_upcoming_commitments",
    }
