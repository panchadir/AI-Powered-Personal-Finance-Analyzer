"""Story 1.2 · AC #3 — shared, framework-agnostic enums.

`direction`, `category_source`, and `criticality` are consumed by both
`finance_app/models.py` (column types) and `services/` (ingestion/engine). They live
under `services/` so the AD-2 boundary (nothing under `services/` imports `finance_app`)
is never crossed. Values are exact, lowercase, no aliases (project-context).
"""
from __future__ import annotations

from enum import Enum

from services.utils.enums import (
    CRITICALITY_DEFAULT,
    CategorySource,
    Criticality,
    Direction,
)


def test_direction_values() -> None:
    assert {d.value for d in Direction} == {"credit", "debit"}


def test_category_source_values() -> None:
    assert {c.value for c in CategorySource} == {"rule", "llm", "user"}


def test_criticality_values() -> None:
    assert {c.value for c in Criticality} == {"critical", "important", "flexible"}


def test_enums_are_str_enums() -> None:
    # str-enum so a plain string column compares equal to the member (SQLite stores str).
    assert isinstance(Direction.credit, str)
    assert Direction.credit == "credit"
    assert CategorySource.llm == "llm"
    assert Criticality.important == "important"


def test_str_enum_membership() -> None:
    assert issubclass(Direction, Enum)
    assert Direction("debit") is Direction.debit


def test_criticality_default_is_important() -> None:
    assert CRITICALITY_DEFAULT == Criticality.important
    assert CRITICALITY_DEFAULT.value == "important"
