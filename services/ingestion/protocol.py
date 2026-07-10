"""The ``StatementParser`` protocol — the ports-and-adapters seam at the ingestion edge.

The architecture spine models statement parsers as one of the two external edges where
ports-and-adapters applies (the other is the LLM callers). Every concrete parser — the
CSV parser (Story 2.2), the PDF chain (Story 2.3), and any Phase-2 source such as an
Account-Aggregator feed — implements this single-method protocol and returns the canonical
``Transaction`` list (AD-6). Downstream code depends on the *protocol*, never on a concrete
parser, so parsers stay swappable and mockable in tests.

It is a ``typing.Protocol`` (structural typing): a parser conforms by shape, without
subclassing. That keeps the third-party ``statementparser`` adapters and our own parsers on
equal footing — neither needs to import a base class from here.
"""
from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from services.ingestion.schema import Transaction

__all__ = ["StatementParser"]


@runtime_checkable
class StatementParser(Protocol):
    """A source-format adapter that yields canonical transactions.

    Contract:

    * ``parse`` takes the path to a single statement file and returns a list of
      :class:`~services.ingestion.schema.Transaction` in canonical shape (AD-6). It must
      not return a parser-specific row type.
    * A parser that cannot read its input must raise a typed ingestion error rather than
      returning an empty list or partial/garbled rows (AD-12, honest refusal — the concrete
      error hierarchy lands with the PDF chain in Story 2.3). ``parse`` returning ``[]`` is
      reserved for a genuinely empty-but-readable statement, not a failure.
    * ``parse`` is pure with respect to the DB: it neither assigns ``user_id`` nor writes
      rows. Persistence and dedup are the caller's job (Story 2.5).
    """

    def parse(self, file_path: Path) -> list[Transaction]:
        """Parse ``file_path`` into canonical transactions, or raise on unreadable input."""
        ...