"""Shared, framework-agnostic enums (Story 1.2, AC #3).

These live under ``services/`` on purpose: both ``finance_app/models.py`` (as column
types) and ``services/`` modules (ingestion, engine) consume them. Placing them here
keeps the AD-2 dependency direction one-way — ``finance_app`` imports from ``services``,
never the reverse (which ``tests/test_service_boundary.py`` enforces).

Values are exact, lowercase, and alias-free (project-context "Enums are exact"):
``direction`` = credit|debit; ``category_source`` = rule|llm|user;
``criticality`` = critical|important|flexible (default ``important``).

They subclass ``str`` so a plain ``str`` column persisted to SQLite round-trips as an
equal value (``Direction.credit == "credit"``). The AD-7 *category* taxonomy enum is a
separate concern and lives in ``services/categorize/schema.py`` (Story 3.2), not here.
"""
from __future__ import annotations

from enum import Enum


class Direction(str, Enum):
    """Transaction flow direction (AD-6 canonical schema)."""

    credit = "credit"
    debit = "debit"


class CategorySource(str, Enum):
    """Provenance of a transaction's category (FR-3.3)."""

    rule = "rule"  # Tier-1 deterministic rules engine
    llm = "llm"  # Tier-2 Claude categorizer
    user = "user"  # Tier-3 "Teach Me" user correction


class Criticality(str, Enum):
    """Commitment criticality tier (FR-4.3). New commitments default to ``important``."""

    critical = "critical"
    important = "important"
    flexible = "flexible"


#: Default criticality for a newly created commitment (FR-4.3 / AC #3).
CRITICALITY_DEFAULT = Criticality.important
