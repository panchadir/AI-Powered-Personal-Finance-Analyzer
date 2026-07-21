"""The ``Categorizer`` protocol — the ports-and-adapters seam at the Tier-2 LLM edge.

Mirrors ``services/ingestion/protocol.py``'s ``StatementParser`` exactly: the architecture
spine models LLM callers as one of the two external edges where ports-and-adapters applies.
The concrete ``ClaudeCategorizer`` (Story 3.2) implements this single-method protocol;
downstream code (the upload pipeline) depends on the *protocol*, never on the concrete
Anthropic-backed implementation, so it stays swappable and mockable in tests.

It is a ``typing.Protocol`` (structural typing): an implementation conforms by shape, without
subclassing.
"""
from __future__ import annotations

from typing import Protocol, Sequence, runtime_checkable

from services.ingestion.schema import Transaction

__all__ = ["Categorizer"]


@runtime_checkable
class Categorizer(Protocol):
    """A Tier-2 categorizer that fills in transactions Tier-1 rules left uncategorized.

    Contract:

    * ``categorize`` takes a sequence of canonical transactions and returns a **new** list
      of the same length and order.
    * Rows whose ``category`` is not ``services.categorize.schema.UNCATEGORIZED`` are
      returned unchanged — this method never re-categorizes a row Tier-1 already decided.
    * For each row it *does* categorize, the result has ``category`` (from the declared
      taxonomy — never free text), ``category_source='llm'``, ``category_confidence``
      (float), and ``reasoning`` set.
    * Never raises for a normal LLM response; a row this method cannot confidently
      categorize is left as ``UNCATEGORIZED`` rather than guessed or dropped.
    """

    def categorize(self, transactions: Sequence[Transaction]) -> list[Transaction]:
        """Return a new list with every UNCATEGORIZED row Tier-2 could resolve filled in."""
        ...
