"""Structural AD-1 guard for the engine test suite (Story 4.2).

``pytest services/engine/`` (here: ``tests/engine/``) is the non-negotiable MVP quality
gate and MUST run with **zero LLM calls** (AD-1, contract §8). The engine is pure
deterministic ``Decimal`` arithmetic — no code path may construct or use an Anthropic
client. This autouse fixture makes any accidental reach for the SDK fail *loudly* rather
than pass on a silent mock, so the guarantee is enforced by the tooling, not by trust.

Reused by Story 4.3's full 13-scenario gate.
"""
from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _forbid_anthropic(monkeypatch: pytest.MonkeyPatch) -> None:
    """Any attempt to build an Anthropic client inside an engine test raises (AD-1)."""

    def _boom(*_args: object, **_kwargs: object) -> None:
        raise AssertionError(
            "engine tests must not construct or use an LLM client (AD-1): "
            "the Safe-to-Spend engine is deterministic and LLM-free."
        )

    try:
        import anthropic
    except ImportError:
        # anthropic not installed in the engine test env → nothing to block, still zero-LLM.
        return

    monkeypatch.setattr(anthropic, "Anthropic", _boom, raising=False)
    monkeypatch.setattr(anthropic, "AsyncAnthropic", _boom, raising=False)
