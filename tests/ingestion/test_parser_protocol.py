"""Story 2.1 acceptance: canonical Transaction schema + StatementParser protocol.

Asserts the AC directly:

* the ``StatementParser`` protocol is a single-method ``parse(file_path) -> list[Transaction]``
  contract, and a stub parser that implements it type-checks and runs;
* everything a parser returns conforms to the canonical schema (AD-6) — all twelve fields
  present, ``Decimal`` money, ``Direction`` enum;
* the schema's honesty guards fire (no float amounts, no raw-string direction) so a
  malformed parser fails loudly at the boundary instead of poisoning the engine (AD-8).

No concrete CSV/PDF parser exists yet (Stories 2.2/2.3) — the stub stands in for them and
proves the contract is implementable and enforced.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from pathlib import Path

import dataclasses

import pytest

from services.ingestion import StatementParser, Transaction
from services.utils.enums import Direction

# The twelve canonical fields the ingestion contract must carry (AD-6).
CANONICAL_FIELDS = {
    "id",
    "user_id",
    "source_file_id",
    "date",
    "description_raw",
    "merchant_normalized",
    "amount",
    "direction",
    "balance_after",
    "category",
    "category_source",
    "category_confidence",
    "created_at",
}


class StubParser:
    """A minimal parser that conforms to StatementParser by shape (structural typing).

    Stands in for the real CSV/PDF parsers until Stories 2.2/2.3; returns two hand-built
    canonical rows so the protocol and schema can be exercised in isolation.
    """

    def parse(self, file_path: Path) -> list[Transaction]:
        return [
            Transaction(
                date="2026-06-01",
                description_raw="  SWIGGY  ",
                amount=Decimal("450.00"),
                direction=Direction.debit,
                balance_after=Decimal("18000.00"),
            ),
            Transaction(
                date="2026-06-30",
                description_raw="SALARY CREDIT ACME CORP",
                amount=Decimal("85000.00"),
                direction=Direction.credit,
                balance_after=Decimal("103000.00"),
            ),
        ]


def test_stub_parser_satisfies_protocol() -> None:
    """A parser conforms by shape — no base class, runtime_checkable isinstance holds."""
    parser: StatementParser = StubParser()
    assert isinstance(parser, StatementParser)


def test_parse_returns_list_of_canonical_transactions() -> None:
    rows = StubParser().parse(Path("dummy.csv"))
    assert isinstance(rows, list)
    assert rows and all(isinstance(t, Transaction) for t in rows)


def test_transaction_exposes_every_canonical_field() -> None:
    """AD-6: the canonical schema is exactly the twelve documented fields."""
    field_names = {f.name for f in dataclasses.fields(Transaction)}
    assert field_names == CANONICAL_FIELDS


def test_parse_time_fields_populated_downstream_fields_none() -> None:
    """A fresh parse knows the money/date fields; persistence & categorization fields default None."""
    txn = StubParser().parse(Path("dummy.csv"))[0]
    assert txn.date == "2026-06-01"
    assert txn.amount == Decimal("450.00")
    assert txn.direction is Direction.debit
    # Assigned by the persistence layer / DB / Epic 3 — unknown at parse time.
    assert txn.user_id is None
    assert txn.source_file_id is None
    assert txn.id is None
    assert txn.created_at is None
    assert txn.category is None
    assert txn.category_source is None


def test_money_fields_must_be_decimal_not_float() -> None:
    """AD-8: a float amount is rejected at construction, not silently accepted."""
    with pytest.raises(TypeError, match="amount must be Decimal"):
        Transaction(
            date="2026-06-01",
            description_raw="x",
            amount=450.0,  # float — forbidden
            direction=Direction.debit,
        )
    with pytest.raises(TypeError, match="balance_after must be Decimal"):
        Transaction(
            date="2026-06-01",
            description_raw="x",
            amount=Decimal("450.00"),
            direction=Direction.debit,
            balance_after=18000.0,  # float — forbidden
        )


def test_direction_must_be_enum_not_raw_string() -> None:
    """AD-6: parsers map source flags to the Direction enum, not bare strings."""
    with pytest.raises(TypeError, match="direction must be a Direction enum"):
        Transaction(
            date="2026-06-01",
            description_raw="x",
            amount=Decimal("450.00"),
            direction="debit",  # raw string — forbidden
        )


def test_transaction_is_frozen() -> None:
    txn = StubParser().parse(Path("dummy.csv"))[0]
    with pytest.raises(dataclasses.FrozenInstanceError):
        txn.amount = Decimal("1.00")  # type: ignore[misc]


def test_with_fields_stamps_persistence_ids_without_mutation() -> None:
    """The persistence layer stamps user_id/source_file_id via an immutable copy."""
    txn = StubParser().parse(Path("dummy.csv"))[0]
    stamped = txn.with_fields(user_id=7, source_file_id=3)
    assert (stamped.user_id, stamped.source_file_id) == (7, 3)
    assert (txn.user_id, txn.source_file_id) == (None, None)  # original untouched
    # Everything else is carried over unchanged.
    assert stamped.amount == txn.amount and stamped.direction is txn.direction


def test_created_at_accepts_db_assigned_datetime() -> None:
    """created_at is DB-assigned; the schema stores whatever the persistence layer sets."""
    stamped = StubParser().parse(Path("dummy.csv"))[0].with_fields(
        id=1, created_at=datetime(2026, 6, 1, 12, 0, 0)
    )
    assert stamped.id == 1
    assert isinstance(stamped.created_at, datetime)