"""Coverage for ``services/narrate/copilot.py``'s ``astream_events`` async generator.

The Anthropic ``AsyncAnthropic`` client is replaced with a fake whose ``messages.stream(...)``
yields scripted text chunks and final messages, so the SSE event contract (token / trace /
error / done) and the tool-use loop (including exhausting ``_MAX_TOOL_ROUNDS``) are exercised
with zero network calls. ``run_tool`` is stubbed so the loop is tested independently of the
concrete tool implementations (those have their own tests in ``test_copilot_tools.py``).
"""
from __future__ import annotations

import contextlib

import pytest

import services.narrate.copilot as copilot_mod
from services.narrate.copilot import astream_events


# --- fakes -----------------------------------------------------------------

class _Block:
    def __init__(self, type_, name=None, id=None, input=None):
        self.type = type_
        self.name = name
        self.id = id
        self.input = input or {}


class _FinalMessage:
    def __init__(self, content):
        self.content = content


class _FakeStream:
    def __init__(self, texts, final):
        self._texts = texts
        self._final = final

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    @property
    def text_stream(self):
        async def _gen():
            for chunk in self._texts:
                yield chunk
        return _gen()

    async def get_final_message(self):
        return self._final


class _FakeMessages:
    def __init__(self, streams):
        self._streams = iter(streams)

    def stream(self, **_kwargs):
        return next(self._streams)


class _FakeClient:
    def __init__(self, streams):
        self.messages = _FakeMessages(streams)


def _install(monkeypatch, streams):
    monkeypatch.setattr(copilot_mod.anthropic, "AsyncAnthropic", lambda **_k: _FakeClient(streams))


def _data_factory():
    return contextlib.nullcontext(object())


async def _collect(**kwargs):
    return [e async for e in astream_events([{"role": "user", "content": "hi"}], **kwargs)]


def _run(coro):
    import asyncio

    return asyncio.run(coro)


# --- tests -----------------------------------------------------------------

class TestAstreamEvents:
    def test_text_only_response_yields_tokens_then_done(self, monkeypatch):
        final = _FinalMessage([_Block("text")])
        _install(monkeypatch, [_FakeStream(["Hello ", "world"], final)])
        events = _run(_collect(user_id=1, data_factory=_data_factory))
        types = [e["type"] for e in events]
        assert types == ["token", "token", "done"]
        assert "".join(e["text"] for e in events if e["type"] == "token") == "Hello world"

    def test_tool_use_round_then_text_emits_trace(self, monkeypatch):
        monkeypatch.setattr(copilot_mod, "run_tool", lambda name, inp, data: {"result": "ok"})
        tool_final = _FinalMessage([_Block("tool_use", name="get_safe_to_spend", id="t1", input={})])
        text_final = _FinalMessage([_Block("text")])
        _install(monkeypatch, [
            _FakeStream([], tool_final),          # round 1: model asks for a tool
            _FakeStream(["Answer."], text_final),  # round 2: model answers in text
        ])
        events = _run(_collect(user_id=7, data_factory=_data_factory))
        types = [e["type"] for e in events]
        assert "trace" in types and types[-1] == "done"
        trace = next(e for e in events if e["type"] == "trace")
        assert trace["sources"] == ["get_safe_to_spend"]

    def test_exhausting_max_rounds_forces_final_text_stream(self, monkeypatch):
        monkeypatch.setattr(copilot_mod, "run_tool", lambda name, inp, data: {"result": "ok"})
        tool_final = _FinalMessage([_Block("tool_use", name="query_transactions", id="t", input={})])
        # Every tool round returns a tool_use → the for-loop's else runs one final no-tools stream.
        streams = [_FakeStream([], tool_final) for _ in range(copilot_mod._MAX_TOOL_ROUNDS)]
        streams.append(_FakeStream(["Final forced answer."], _FinalMessage([_Block("text")])))
        _install(monkeypatch, streams)
        events = _run(_collect(user_id=2, data_factory=_data_factory))
        assert any(e["type"] == "token" and "Final forced" in e["text"] for e in events)
        assert events[-1]["type"] == "done"

    def test_streaming_exception_emits_error_then_done(self, monkeypatch):
        class _BoomStream(_FakeStream):
            async def get_final_message(self):
                raise RuntimeError("upstream 500")

        _install(monkeypatch, [_BoomStream(["partial"], None)])
        events = _run(_collect(user_id=9, data_factory=_data_factory))
        types = [e["type"] for e in events]
        assert "error" in types and types[-1] == "done"
        err = next(e for e in events if e["type"] == "error")
        assert "couldn't finish" in err["text"]
