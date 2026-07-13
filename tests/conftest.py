"""Shared harness for driving Reflex ``rx.State`` event handlers in unit tests.

The app's own tests deliberately extract pure logic out of ``rx.State`` classes and leave the
event-handler wiring to app-verification (see ``tests/test_transactions_state.py``'s docstring).
This harness closes that coverage gap by driving the handlers directly, without a running Reflex
server, using three pieces:

1. ``db_engine`` — a throwaway SQLite DB with every app table created.
2. ``rx_session`` — monkeypatches ``rx.session()`` so any handler's ``with rx.session() as s``
   block runs against that SQLite DB instead of the configured Postgres.
3. ``make_state`` — builds the *full* Reflex substate tree from the real root state and returns
   the requested wired substate instance. Building from the root is what makes writes to
   **inherited** vars (e.g. ``auth_token`` defined on ``AuthState``) work; a bare
   ``SomeState()`` has ``parent_state is None`` and raises on inherited-var assignment.

Reflex only permits direct state instantiation inside a testing env (it keys off
``PYTEST_CURRENT_TEST``), so these helpers are inherently test-only.

Async event handlers are async generators; use :func:`drive` to run one to completion and
collect nothing (state mutations are the observable effect).
"""
from __future__ import annotations

import contextlib
from typing import Any

import pytest
import sqlmodel

import finance_app.models  # noqa: F401  — registers every app table on the metadata


@pytest.fixture
def db_engine(tmp_path):
    """A fresh SQLite engine with all app tables, isolated per test."""
    engine = sqlmodel.create_engine(f"sqlite:///{tmp_path / 'app.db'}")
    sqlmodel.SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture
def db_session(db_engine):
    """A plain session on the harness DB, for arranging rows outside a handler."""
    with sqlmodel.Session(db_engine) as session:
        yield session


@pytest.fixture
def rx_session(db_engine, monkeypatch):
    """Point every ``rx.session()`` call at the harness SQLite DB for the test's duration."""
    import reflex as rx

    @contextlib.contextmanager
    def _fake_session(*_args, **_kwargs):
        with sqlmodel.Session(db_engine) as session:
            yield session

    monkeypatch.setattr(rx, "session", _fake_session)
    return db_engine


def _patch_router(node, params: dict[str, str] | None, client_token: str | None) -> None:
    """Replace ``node.router`` with a copy carrying ``params`` and/or ``client_token``.

    ``RouterData`` (and its nested page/session data) are frozen, so we rebuild by copy.
    ``client_token`` matters for login: ``_login`` rotates ``auth_token`` to
    ``router.session.client_token`` after clearing any prior token.
    """
    import dataclasses

    router = node.router
    router = getattr(router, "__wrapped__", router)  # unwrap Reflex's MutableProxy
    update: dict[str, Any] = {}
    if params is not None:
        update["_page"] = dataclasses.replace(router.page, params=dict(params))
    if client_token is not None:
        update["session"] = dataclasses.replace(router.session, client_token=client_token)
    if update:
        node.router = dataclasses.replace(router, **update)


@pytest.fixture
def make_state(rx_session):
    """Factory: build a fully-wired substate instance ready to have its handlers called.

    Args to the returned factory:
      ``state_cls``    — the ``rx.State`` subclass under test.
      ``auth_token``   — optional; written to the (inherited) cookie var.
      ``params``       — optional; becomes ``self.router.page.params`` for ``on_load`` handlers.
      ``client_token`` — optional; becomes ``self.router.session.client_token`` (login token rotation).
    """
    import reflex as rx

    def _make(
        state_cls,
        *,
        auth_token: str | None = None,
        params: dict[str, str] | None = None,
        client_token: str | None = None,
    ):
        root = rx.State()
        node: Any = root
        for part in state_cls.get_full_name().split(".")[1:]:
            node = node.substates[part]
        if auth_token is not None:
            node.auth_token = auth_token
        _patch_router(node, params, client_token)
        return node

    return _make


@pytest.fixture
def seed_auth(db_session):
    """Create a real user + live ``LocalAuthSession`` in the harness DB; return ``(user_id, token)``.

    Handlers resolve the caller via ``user_for_token(session, self.auth_token)``, so a test that
    drives an authenticated handler seeds a session here and passes the same ``token`` as the
    state's ``auth_token``.
    """
    import datetime

    from reflex_local_auth.auth_session import LocalAuthSession

    from finance_app.state.auth_state import register_new_user

    def _seed(token: str = "test-token", email: str = "u@example.com", password: str = "supersecret8"):
        result = register_new_user(db_session, email, password)
        assert result.ok, result.error
        db_session.add(
            LocalAuthSession(  # type: ignore[call-arg]
                user_id=result.user_id,
                session_id=token,
                expiration=datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=7),
            )
        )
        db_session.commit()
        return result.user_id, token

    return _seed


async def _drain(awaitable_or_gen) -> list[Any]:
    # Reflex handlers come in two shapes: async *generators* that ``yield`` to flush state, and
    # plain coroutines (``async def`` with a ``return``). Handle both transparently.
    if hasattr(awaitable_or_gen, "__aiter__"):
        collected: list[Any] = []
        async for value in awaitable_or_gen:
            collected.append(value)
        return collected
    return [await awaitable_or_gen]


def drive_background(state, handler, *args) -> None:
    """Run a Reflex ``@rx.event(background=True)`` handler's coroutine to completion.

    Background handlers are wrapped ``EventHandler`` objects; the underlying coroutine function
    is on ``.fn`` and takes the state instance as ``self``. ``async with self`` inside works
    against the wired substate the harness builds.
    """
    import asyncio

    asyncio.run(handler.fn(state, *args))


def drive(async_gen) -> list[Any]:
    """Run an async event-generator handler to completion, returning any yielded values.

    Reflex async event handlers ``yield`` bare ``None`` (or event specs like ``rx.redirect``)
    to flush state mid-handler; the observable result is usually the accumulated state
    mutation, so callers typically ignore the return. No ``pytest-asyncio`` needed — this
    drives the coroutine itself via ``asyncio.run``.
    """
    import asyncio

    return asyncio.run(_drain(async_gen))
