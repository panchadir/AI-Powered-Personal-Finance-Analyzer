"""Regression tests for ``DbCopilotData``'s real DB queries (finance_app/state/copilot_data.py).

This is the concrete provider behind the Copilot's read-only tools (``services/narrate/tools.py``
only defines the ``CopilotData`` Protocol + dispatcher, and is tested against a fake provider in
``tests/narrate/test_copilot_tools.py``). No test previously exercised this module's actual query
behavior — this locks in the ``user_id`` scoping (AD-4 / IDOR guard) the Copilot tools depend on
for `query_transactions` and `get_spending_by_category`.
"""
from __future__ import annotations

from decimal import Decimal

import pytest
import sqlmodel

from finance_app.models import Transaction
from finance_app.state.copilot_data import DbCopilotData


@pytest.fixture
def session(tmp_path):
    engine = sqlmodel.create_engine(f"sqlite:///{tmp_path / 'copilot_data.db'}")
    sqlmodel.SQLModel.metadata.create_all(engine)
    with sqlmodel.Session(engine) as s:
        yield s


def _add_txn(session, **overrides) -> None:
    defaults = dict(
        user_id=1,
        date="2026-06-15",
        description_raw="SWIGGY",
        merchant_normalized="Swiggy",
        amount=Decimal("250.00"),
        direction="debit",
        category="Dining",
    )
    defaults.update(overrides)
    session.add(Transaction(**defaults))  # type: ignore[call-arg]
    session.commit()


class TestQueryTransactions:
    def test_returns_only_the_requesting_users_rows(self, session):
        _add_txn(session, user_id=1, amount=Decimal("100"))
        _add_txn(session, user_id=2, amount=Decimal("999"))  # another user's row
        data = DbCopilotData(session, user_id=1)

        result = data.query_transactions(category=None, direction=None, limit=None)
        assert result["count"] == 1
        assert result["transactions"][0]["amount"] == "₹100"

    def test_filters_by_category_and_direction(self, session):
        _add_txn(session, category="Dining", direction="debit", amount=Decimal("300"))
        _add_txn(session, category="Groceries", direction="debit", amount=Decimal("500"))
        _add_txn(session, category="Dining", direction="credit", amount=Decimal("50"))
        data = DbCopilotData(session, user_id=1)

        result = data.query_transactions(category="Dining", direction="debit", limit=None)
        assert result["count"] == 1
        assert result["transactions"][0]["amount"] == "₹300"

    def test_respects_the_limit_cap_at_fifty(self, session):
        for i in range(60):
            _add_txn(session, date=f"2026-06-{(i % 28) + 1:02d}", amount=Decimal("10"))
        data = DbCopilotData(session, user_id=1)

        result = data.query_transactions(category=None, direction=None, limit=999)
        assert result["count"] == 50


class TestGetSpendingByCategory:
    def test_sums_debits_grouped_by_category_excluding_credits(self, session):
        _add_txn(session, category="Dining", direction="debit", amount=Decimal("300"))
        _add_txn(session, category="Dining", direction="debit", amount=Decimal("200"))
        _add_txn(session, category="Groceries", direction="debit", amount=Decimal("500"))
        _add_txn(session, category="Dining", direction="credit", amount=Decimal("9999"))
        data = DbCopilotData(session, user_id=1)

        result = data.get_spending_by_category()
        by_category = {row["category"]: row["total"] for row in result["by_category"]}
        assert by_category["Dining"] == "₹500"
        assert by_category["Groceries"] == "₹500"

    def test_scopes_to_the_requesting_user_only(self, session):
        _add_txn(session, user_id=1, category="Dining", amount=Decimal("100"))
        _add_txn(session, user_id=2, category="Dining", amount=Decimal("99999"))
        data = DbCopilotData(session, user_id=1)

        result = data.get_spending_by_category()
        assert result["by_category"] == [{"category": "Dining", "total": "₹100"}]

    def test_reports_unavailable_when_no_categorised_spending_exists(self, session):
        data = DbCopilotData(session, user_id=1)
        result = data.get_spending_by_category()
        assert result["available"] is False
