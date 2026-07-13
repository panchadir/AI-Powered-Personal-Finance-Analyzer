"""Handler coverage for ``finance_app/state/copilot_state.py``.

``astream_events`` (the LLM streaming service) is monkeypatched to a fake async generator so
no network call happens; that lets ``send_message``'s token/trace/done and error paths, the
no-data synthetic reply, and ``load_history``'s DB + URL-param handling all run deterministically
through the ``make_state`` harness.
"""
from __future__ import annotations

import pytest

import finance_app.state.copilot_state as copilot_mod
from finance_app.models import ChatMessage, Insight, Transaction
from finance_app.state.copilot_state import COPILOT_NO_DATA_RESPONSE, CopilotState
from tests.conftest import drive


def _seed_txn(session, uid):
    session.add(Transaction(  # type: ignore[call-arg]
        user_id=uid, date="2026-06-01", description_raw="SWIGGY",
        amount=__import__("decimal").Decimal("500"), direction="debit", category="Food & Dining",
    ))
    session.commit()


def _fake_stream_ok(messages, *, user_id, data_factory, api_key=None):
    async def _gen():
        yield {"type": "token", "text": "Hello "}
        yield {"type": "token", "text": "there."}
        yield {"type": "trace", "sources": ["get_safe_to_spend"]}
        yield {"type": "done"}
    return _gen()


def _fake_stream_error(messages, *, user_id, data_factory, api_key=None):
    async def _gen():
        yield {"type": "error", "text": "Something broke."}
        yield {"type": "done"}
    return _gen()


# ---------------------------------------------------------------------------
# Sync handlers
# ---------------------------------------------------------------------------

class TestSyncHandlers:
    def test_set_input(self, make_state):
        s = make_state(CopilotState)
        s.set_input("hi")
        assert s.input_value == "hi"

    def test_handle_key_down_enter_triggers_send(self, make_state):
        s = make_state(CopilotState)
        s.input_value = "question"
        assert s.handle_key_down("Enter") is not None

    def test_handle_key_down_ignores_other_keys_and_empty(self, make_state):
        s = make_state(CopilotState)
        s.input_value = ""
        assert s.handle_key_down("Enter") is None
        s.input_value = "x"
        assert s.handle_key_down("a") is None

    def test_dismiss_context_clears_chip(self, make_state):
        s = make_state(CopilotState)
        s.context_pattern_name = "Post-payday spike"
        s.context_insight_id = 5
        s.input_value = "prefilled"
        s.dismiss_context()
        assert s.context_pattern_name == "" and s.context_insight_id == 0 and s.input_value == ""

    def test_send_quick_prompt_sets_input_and_sends(self, make_state):
        s = make_state(CopilotState)
        assert s.send_quick_prompt("How am I doing?") is not None
        assert s.input_value == "How am I doing?"


# ---------------------------------------------------------------------------
# load_history
# ---------------------------------------------------------------------------

class TestLoadHistory:
    def test_no_user_is_a_silent_return(self, make_state):
        s = make_state(CopilotState, auth_token="nope")
        drive(s.load_history())  # must not raise
        assert s.messages == []

    def test_loads_prior_messages_and_flags_data(self, make_state, seed_auth, db_session):
        uid, token = seed_auth()
        _seed_txn(db_session, uid)
        db_session.add(ChatMessage(user_id=uid, role="user", content="hi"))  # type: ignore[call-arg]
        db_session.add(ChatMessage(user_id=uid, role="assistant", content="hello", trace_sources='["Income"]'))  # type: ignore[call-arg]
        db_session.commit()
        s = make_state(CopilotState, auth_token=token)
        drive(s.load_history())
        assert s.has_transactions is True
        assert [m.role for m in s.messages] == ["user", "assistant"]
        assert s.messages[1].trace_sources == ["Income"]

    def test_active_insight_param_sets_context_chip(self, make_state, seed_auth, db_session):
        uid, token = seed_auth()
        insight = Insight(  # type: ignore[call-arg]
            user_id=uid, pattern_name="Post-payday spike", observation="x", evidence="[]",
            explanation="x", effect="x", action_suggestion="Spread it out.", status="active",
            severity="critical", dedup_key="k1",
        )
        db_session.add(insight)
        db_session.commit()
        db_session.refresh(insight)
        s = make_state(CopilotState, auth_token=token, params={"insight": str(insight.id), "pre": "prefill me"})
        drive(s.load_history())
        assert s.context_insight_id == insight.id
        assert s.context_pattern_name == "Post-payday spike"
        assert s.input_value == "prefill me"

    def test_dismissed_insight_param_clears_context(self, make_state, seed_auth, db_session):
        uid, token = seed_auth()
        insight = Insight(  # type: ignore[call-arg]
            user_id=uid, pattern_name="Zombie subscriptions", observation="x", evidence="[]",
            explanation="x", effect="x", action_suggestion="cancel", status="dismissed",
            severity="important", dedup_key="k2",
        )
        db_session.add(insight)
        db_session.commit()
        db_session.refresh(insight)
        s = make_state(CopilotState, auth_token=token, params={"insight": str(insight.id)})
        drive(s.load_history())
        assert s.context_insight_id == 0 and s.context_pattern_name == ""

    def test_malformed_insight_param_is_ignored(self, make_state, seed_auth):
        _uid, token = seed_auth()
        s = make_state(CopilotState, auth_token=token, params={"insight": "not-an-int"})
        drive(s.load_history())
        assert s.context_insight_id == 0

    def test_no_insight_param_clears_stale_context(self, make_state, seed_auth):
        _uid, token = seed_auth()
        s = make_state(CopilotState, auth_token=token)
        s.context_insight_id = 99
        s.context_pattern_name = "stale"
        drive(s.load_history())
        assert s.context_insight_id == 0 and s.context_pattern_name == ""


# ---------------------------------------------------------------------------
# send_message
# ---------------------------------------------------------------------------

class TestSendMessage:
    def test_empty_input_is_noop(self, make_state, seed_auth):
        _uid, token = seed_auth()
        s = make_state(CopilotState, auth_token=token)
        s.input_value = "   "
        drive(s.send_message())
        assert s.messages == []

    def test_no_data_returns_synthetic_reply(self, make_state, seed_auth, db_session):
        uid, token = seed_auth()
        s = make_state(CopilotState, auth_token=token)
        s.has_transactions = False
        s.input_value = "How am I doing?"
        drive(s.send_message())
        assert [m.role for m in s.messages] == ["user", "assistant"]
        assert s.messages[1].content == COPILOT_NO_DATA_RESPONSE
        from sqlmodel import select
        persisted = db_session.exec(select(ChatMessage).where(ChatMessage.user_id == uid)).all()
        assert len(persisted) == 2

    def test_streaming_reply_persists_assistant_turn(self, make_state, seed_auth, db_session, monkeypatch):
        monkeypatch.setattr(copilot_mod, "astream_events", _fake_stream_ok)
        uid, token = seed_auth()
        s = make_state(CopilotState, auth_token=token)
        s.has_transactions = True
        s.context_insight_id = 3  # exercise the insight-context annotation branch
        s.input_value = "What's my biggest spend?"
        drive(s.send_message())
        assert s.streaming is False
        assert s.messages[-1].role == "assistant" and s.messages[-1].content == "Hello there."
        assert s.messages[-1].trace_sources == ["Safe-to-Spend"]
        from sqlmodel import select
        assistant_rows = db_session.exec(
            select(ChatMessage).where(ChatMessage.user_id == uid, ChatMessage.role == "assistant")
        ).all()
        assert len(assistant_rows) == 1

    def test_error_response_is_not_persisted(self, make_state, seed_auth, db_session, monkeypatch):
        monkeypatch.setattr(copilot_mod, "astream_events", _fake_stream_error)
        uid, token = seed_auth()
        s = make_state(CopilotState, auth_token=token)
        s.has_transactions = True
        s.input_value = "hello"
        drive(s.send_message())
        assert s.streaming is False
        assert s.messages[-1].content == "Something broke."
        from sqlmodel import select
        assistant_rows = db_session.exec(
            select(ChatMessage).where(ChatMessage.user_id == uid, ChatMessage.role == "assistant")
        ).all()
        assert assistant_rows == []  # error sentinel never persisted


class TestSendMessageResilience:
    def test_utcnow_is_timezone_aware(self):
        assert copilot_mod._utcnow().tzinfo is not None

    def test_stream_that_raises_midway_resets_streaming_in_finally(self, make_state, seed_auth, monkeypatch):
        def _fake_stream_raises(messages, *, user_id, data_factory, api_key=None):
            async def _gen():
                yield {"type": "token", "text": "partial"}
                raise RuntimeError("socket dropped")
            return _gen()

        monkeypatch.setattr(copilot_mod, "astream_events", _fake_stream_raises)
        _uid, token = seed_auth()
        s = make_state(CopilotState, auth_token=token)
        s.has_transactions = True
        s.input_value = "hi"
        with pytest.raises(RuntimeError):
            drive(s.send_message())
        # The finally block must have cleared the streaming flags despite the abnormal exit.
        assert s.streaming is False and s.streaming_content == ""

    def test_no_data_persist_failure_is_swallowed(self, make_state, seed_auth, monkeypatch):
        # A DB failure while saving the synthetic reply must not surface to the user.
        def _boom(*a, **k):
            raise RuntimeError("db down")

        monkeypatch.setattr(copilot_mod, "ChatMessage", _boom)
        _uid, token = seed_auth()
        s = make_state(CopilotState, auth_token=token)
        s.has_transactions = False
        s.input_value = "How am I doing?"
        drive(s.send_message())  # must not raise
        assert s.messages[-1].content == COPILOT_NO_DATA_RESPONSE

    def test_streaming_persist_failures_are_swallowed(self, make_state, seed_auth, monkeypatch):
        monkeypatch.setattr(copilot_mod, "astream_events", _fake_stream_ok)

        def _boom(*a, **k):
            raise RuntimeError("db down")

        monkeypatch.setattr(copilot_mod, "ChatMessage", _boom)
        _uid, token = seed_auth()
        s = make_state(CopilotState, auth_token=token)
        s.has_transactions = True
        s.input_value = "What's my biggest spend?"
        drive(s.send_message())  # user + assistant persist both fail, both swallowed
        assert s.messages[-1].content == "Hello there." and s.streaming is False
