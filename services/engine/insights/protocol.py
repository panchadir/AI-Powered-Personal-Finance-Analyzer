"""The ``InsightDetector`` protocol (Story 7.1, AC #2).

A detector is any object with a ``pattern_name`` and a ``detect(ctx)`` method returning a
list of candidates — empty when the pattern does not fire (never ``None``, never a raised
exception for "no match"). Defined as a ``typing.Protocol`` so detectors need no shared
base class (composition over inheritance; project general standards).
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from services.engine.insights.types import InsightCandidate, InsightContext


@runtime_checkable
class InsightDetector(Protocol):
    """Structural contract every FR-8.1 detector satisfies."""

    pattern_name: str

    def detect(self, ctx: InsightContext) -> list[InsightCandidate]:
        """Return the candidates this detector finds in ``ctx`` (``[]`` if none)."""
        ...
