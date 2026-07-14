"""End-to-end performance harness for the Reflex finance app.

Measures REAL client->server->client latency of every ``@rx.event`` handler by speaking
the Reflex socket.io wire protocol (namespace ``/_event``, message ``"event"``), exactly
as the browser does. Read-only with respect to application source.

HOW COMPLETION IS DETECTED (this is the crux of the measurement)
---------------------------------------------------------------
Reflex 0.9.6 has NO per-event "done" marker on the wire (``StateUpdate.final`` is
deprecated and never set). But ``reflex_base.event.processor.EventProcessor`` keeps a
**per-token deque** (``_token_queues``): non-background events for a given client token
are executed strictly one at a time, and the next is only dispatched from the previous
one's ``_finish_task`` done-callback.

So: emit the target event, then immediately emit a trivial SENTINEL event on the same
token. The sentinel's delta cannot be produced until the target handler has fully
returned. Time from ``emit(target)`` to ``delta(sentinel)`` is therefore an upper bound
on the target's full server-side execution, and subtracting the separately-measured
sentinel round-trip gives the handler cost.

Background events (``@rx.event(background=True)``) deliberately bypass this ordering, so
they are correctly EXCLUDED from the foreground measurement.

Run INSIDE the container:
    docker compose exec -T app python /app/perf_harness.py --phase baseline
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import statistics
import sys
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

import httpx
import socketio

BACKEND = os.environ.get("PERF_BACKEND", "http://localhost:8000")
NS = "/_event"
BUDGET_MS = 3000.0

DEMO_EMAIL = "demo@example.com"
DEMO_PASSWORD = "demodemo1"

# --- Real state names (introspected from reflex.state.all_base_state_classes) ---
ROOT = "reflex___state____state"
AUTH = f"{ROOT}.finance_app___state___auth_state____auth_state"
LOGIN = f"{AUTH}.finance_app___state___auth_state____login_state"
REGISTER = f"{AUTH}.finance_app___state___auth_state____register_state"
DASH = f"{AUTH}.finance_app___state___dashboard_state____dashboard_state"
TXNS = f"{AUTH}.finance_app___state___transactions_state____transactions_state"
INSIGHTS = f"{AUTH}.finance_app___state___insights_state____insights_state"
COMMIT = f"{AUTH}.finance_app___state___commitments_state____commitments_state"
COPILOT = f"{AUTH}.finance_app___state___copilot_state____copilot_state"
UPLOAD = f"{AUTH}.finance_app___state___upload_state____upload_state"

# A trivial, DB-free bool toggle. Always dirties exactly one var -> always emits a delta.
# No handler under test ever writes `drillin_open`, so its presence is an unambiguous
# "the previously-queued event has finished" marker.
SENTINEL = f"{DASH}.toggle_drillin"
SENTINEL_VAR = "drillin_open"


def dvars(update: dict, state: str) -> dict:
    return (update.get("delta") or {}).get(state, {})


def has_var(update: dict, state: str, var: str) -> bool:
    return f"{var}_rx_state_" in dvars(update, state)


def getvar(update: dict, state: str, var: str, default: Any = None) -> Any:
    return dvars(update, state).get(f"{var}_rx_state_", default)


def find_var(updates: list, state: str, var: str, default: Any = None) -> Any:
    """Last value of `var` seen across a list of updates."""
    out = default
    for u in updates:
        if has_var(u, state, var):
            out = getvar(u, state, var)
    return out


@dataclass
class Sample:
    ms: float
    ok: bool
    evidence: str
    deltas: int
    first_delta_ms: float | None = None


@dataclass
class Result:
    handler: str
    method: str
    samples: list[Sample] = field(default_factory=list)
    note: str = ""
    error: str = ""

    def times(self) -> list[float]:
        return [s.ms for s in self.samples if s.ok]

    def stats(self) -> dict:
        t = sorted(self.times())
        if not t:
            return {"n": 0, "verified": 0}
        def pct(p: float) -> float:
            if len(t) == 1:
                return t[0]
            k = (len(t) - 1) * p
            lo, hi = int(k), min(int(k) + 1, len(t) - 1)
            return t[lo] + (t[hi] - t[lo]) * (k - lo)
        p95 = pct(0.95)
        mx = t[-1]
        # `_LOADER_MIN_SECONDS = 0.8` (dashboard/transactions/insights) fires ONLY when
        # `loaded` is still False, i.e. the first call per session. Mixing that one cold
        # sample into the percentiles is misleading, so expose the split.
        ok_seq = [s.ms for s in self.samples if s.ok]
        cold = ok_seq[0] if ok_seq else None
        warm = sorted(ok_seq[1:])
        return {
            "n": len(t),
            "min": round(t[0], 1),
            "p50": round(statistics.median(t), 1),
            "p95": round(p95, 1),
            "max": round(mx, 1),
            "mean": round(statistics.fmean(t), 1),
            "verified": sum(1 for s in self.samples if s.ok),
            "pass": p95 <= BUDGET_MS and mx <= BUDGET_MS,
            "breach": ("p95+max" if p95 > BUDGET_MS else "max-only") if mx > BUDGET_MS else "",
            "evidence": next((s.evidence for s in self.samples if s.ok), ""),
            "cold_first_call_ms": round(cold, 1) if cold is not None else None,
            "warm_p50": round(statistics.median(warm), 1) if warm else None,
            "warm_max": round(warm[-1], 1) if warm else None,
            "first_delta_p50": round(
                statistics.median([s.first_delta_ms for s in self.samples
                                   if s.ok and s.first_delta_ms is not None]), 1
            ) if any(s.first_delta_ms is not None for s in self.samples if s.ok) else None,
        }


class ReflexClient:
    """Speaks the Reflex socket.io protocol like the browser does."""

    def __init__(self, path: str = "/dashboard") -> None:
        self.token = str(uuid.uuid4())
        # aiohttp's websocket client defaults to max_msg_size=4 MiB and hard-closes the
        # connection on a larger frame. TransactionsState.load_transactions pushes a
        # 4.22 MB delta at 20k rows, which trips exactly that limit. Disable the cap (0 =
        # unlimited) so we measure the app's real latency instead of our client's ceiling.
        # NOTE: the fact that a stock WS client cannot even receive this frame is itself a
        # finding, reported separately.
        self.sio = socketio.AsyncClient(
            reconnection=False,
            websocket_extra_options={"max_msg_size": 0},
        )
        self.updates: list[tuple[float, dict]] = []
        self.path = path
        self._ev = asyncio.Event()

    async def connect(self) -> None:
        @self.sio.on("event", namespace=NS)
        async def _on(update):  # noqa: ANN001
            self.updates.append((time.perf_counter(), update))
            self._ev.set()

        await self.sio.connect(
            f"{BACKEND}?token={self.token}",
            socketio_path=NS,
            namespaces=[NS],
            transports=["websocket"],
        )
        await self.emit(f"{ROOT}.hydrate", {})
        await asyncio.sleep(0.8)
        self.updates.clear()

    async def emit(self, name: str, payload: dict, path: str | None = None) -> None:
        p = path or self.path
        await self.sio.emit(
            "event",
            {"name": name, "payload": payload,
             "router_data": {"pathname": p, "asPath": p, "query": {}}},
            namespace=NS,
        )

    async def _await_sentinel(self, timeout: float) -> list[dict]:
        """Wait until the sentinel's delta lands; return every update up to and incl. it."""
        deadline = time.perf_counter() + timeout
        seen = 0
        while time.perf_counter() < deadline:
            self._ev.clear()
            for i in range(seen, len(self.updates)):
                if has_var(self.updates[i][1], DASH, SENTINEL_VAR):
                    return [u for _, u in self.updates[: i + 1]]
            seen = len(self.updates)
            try:
                await asyncio.wait_for(self._ev.wait(), timeout=max(0.05, deadline - time.perf_counter()))
            except asyncio.TimeoutError:
                break
        raise TimeoutError("sentinel never arrived")

    async def run(self, name: str, payload: dict, path: str | None = None,
                  timeout: float = 120.0) -> tuple[float, list[dict], float | None]:
        """Emit `name`, then the sentinel. Returns (ms, updates, first_delta_ms)."""
        self.updates.clear()
        self._ev.clear()
        t0 = time.perf_counter()
        await self.emit(name, payload, path)
        await self.emit(SENTINEL, {}, path)
        ups = await self._await_sentinel(timeout)
        ms = (time.perf_counter() - t0) * 1000.0
        first = None
        if self.updates:
            first = (self.updates[0][0] - t0) * 1000.0
        return ms, ups, first

    async def fire(self, name: str, payload: dict, path: str | None = None,
                   timeout: float = 120.0) -> list[dict]:
        """Run a setup/teardown event to completion, discarding timing."""
        _, ups, _ = await self.run(name, payload, path, timeout)
        return ups

    async def login(self, email: str = DEMO_EMAIL, password: str = DEMO_PASSWORD) -> dict:
        ups = await self.fire(f"{LOGIN}.handle_login",
                              {"form_data": {"email": email, "password": password}}, "/login")
        uid = find_var(ups, AUTH, "authenticated_user", {}) or {}
        tok = find_var(ups, AUTH, "auth_token", "")
        if not tok or (uid or {}).get("id", -1) < 0:
            raise RuntimeError(f"LOGIN FAILED for {email}: user={uid} token={bool(tok)}")
        return uid

    async def close(self) -> None:
        try:
            await self.sio.disconnect()
        except Exception:
            pass


# ----------------------------------------------------------------------------
# Verifiers: prove the handler actually did work (a fast bail-out is a FALSE PASS)
# ----------------------------------------------------------------------------
def v_dashboard(ups: list[dict]) -> tuple[bool, str]:
    sts = find_var(ups, DASH, "safe_to_spend_today")
    loaded = find_var(ups, DASH, "loaded")
    briefing = find_var(ups, DASH, "briefing")
    if not loaded:
        return False, "loaded never set (bailed / redirected?)"
    if sts is None:
        return False, "no safe_to_spend_today"
    return True, f"safe_to_spend={sts!r} briefing={'yes(%dch)' % len(briefing) if briefing else 'NO'}"


def v_transactions(ups: list[dict]) -> tuple[bool, str]:
    rows = find_var(ups, TXNS, "rows")
    if rows is None:
        return False, "no rows delta"
    if not isinstance(rows, list) or not rows:
        return False, f"rows empty ({rows!r})"
    return True, f"{len(rows)} rows"


def v_insights(ups: list[dict]) -> tuple[bool, str]:
    loaded = find_var(ups, INSIGHTS, "loaded")
    cards = find_var(ups, INSIGHTS, "cards") or []
    wins = find_var(ups, INSIGHTS, "win_cards") or []
    hd = find_var(ups, INSIGHTS, "has_data")
    if not loaded:
        return False, "loaded never set"
    return True, f"cards={len(cards)} wins={len(wins)} has_data={hd}"


def v_commitments(ups: list[dict]) -> tuple[bool, str]:
    c = find_var(ups, COMMIT, "commitments")
    prot = find_var(ups, COMMIT, "protecting_total")
    if c is None:
        return False, "no commitments delta"
    return True, f"{len(c)} commitments protecting={prot!r}"


def v_delta(state: str, var: str, label: str = "") -> Callable:
    def _v(ups: list[dict]) -> tuple[bool, str]:
        for u in ups:
            if has_var(u, state, var):
                return True, f"{label or var}={json.dumps(getvar(u, state, var))[:70]}"
        return False, f"no {var} delta"
    return _v


def v_login(ups: list[dict]) -> tuple[bool, str]:
    u = find_var(ups, AUTH, "authenticated_user", {}) or {}
    if (u or {}).get("id", -1) < 0:
        return False, f"not authenticated: {u}"
    return True, f"user_id={u.get('id')} {u.get('username')}"


def v_copilot_history(ups: list[dict]) -> tuple[bool, str]:
    for u in ups:
        if has_var(u, COPILOT, "messages") or has_var(u, COPILOT, "loaded"):
            m = find_var(ups, COPILOT, "messages") or []
            return True, f"{len(m)} messages"
    return False, "no messages/loaded delta"


def v_send_message(ups: list[dict]) -> tuple[bool, str]:
    """A reply is only a REAL LLM call if streaming actually produced content.

    CopilotState.send_message short-circuits to a canned string when
    `has_transactions` is False -- that path never touches the LLM and would be a
    false PASS. We assert we saw streaming_content grow (the token stream).
    """
    msgs = find_var(ups, COPILOT, "messages") or []
    streamed = any(has_var(u, COPILOT, "streaming_content") for u in ups)
    if not msgs:
        return False, "no messages delta"
    last = msgs[-1] if isinstance(msgs, list) else {}
    content = (last or {}).get("content_rx_state_") or (last or {}).get("content") or ""
    if not streamed:
        return False, f"NO token stream -> canned no-data reply, LLM not called: {str(content)[:50]!r}"
    return True, f"{len(msgs)} msgs, streamed, reply={str(content)[:55]!r}"


# ============================================================================
# Scenario driving
# ============================================================================
RESULTS_DIR = Path(__file__).parent / "results"


async def sentinel_baseline(c: ReflexClient, n: int = 20) -> dict:
    """Round-trip cost of the sentinel itself = harness+network+framework overhead."""
    ts = []
    for _ in range(n):
        t0 = time.perf_counter()
        c.updates.clear(); c._ev.clear()
        await c.emit(SENTINEL, {})
        await c._await_sentinel(15)
        ts.append((time.perf_counter() - t0) * 1000)
    ts.sort()
    return {"n": n, "min": round(ts[0], 2), "p50": round(statistics.median(ts), 2),
            "max": round(ts[-1], 2), "mean": round(statistics.fmean(ts), 2)}


async def measure(c: ReflexClient, label: str, name: str, payload: dict,
                  verify: Callable, n: int, path: str = "/dashboard",
                  setup: Callable | None = None, timeout: float = 180.0,
                  note: str = "") -> Result:
    r = Result(handler=label, method="socket.io /_event (real E2E round-trip)", note=note)
    for i in range(n):
        try:
            if setup is not None:
                pay = await setup(c, i)
                if pay is None:
                    r.error = r.error or "setup could not produce a driveable fixture"
                    break
                if isinstance(pay, dict):
                    payload = pay
            ms, ups, first = await c.run(name, payload, path, timeout)
            ok, ev = verify(ups)
            r.samples.append(Sample(ms=ms, ok=ok, evidence=ev, deltas=len(ups), first_delta_ms=first))
            if not ok:
                print(f"    !! sample {i} UNVERIFIED: {ev}")
        except Exception as e:  # noqa: BLE001
            r.error = f"{type(e).__name__}: {e}"
            print(f"    !! sample {i} ERROR: {r.error}")
            break
    s = r.stats()
    if s.get("n"):
        vflag = "PASS" if s["pass"] else f"FAIL({s['breach']})"
        print(f"  {label:<34} n={s['n']:<3} p50={s['p50']:>8.1f}  p95={s['p95']:>8.1f}  "
              f"max={s['max']:>8.1f}  {vflag:<12} | {s['evidence'][:58]}")
    else:
        print(f"  {label:<34} NO VERIFIED SAMPLES  err={r.error}")
    return r


def txn_count(user_id: int = 2) -> int:
    import sqlmodel
    from finance_app.models import Transaction
    eng = sqlmodel.create_engine(os.environ["DATABASE_URL"])
    with sqlmodel.Session(eng) as s:
        return len(s.exec(sqlmodel.select(Transaction.id).where(Transaction.user_id == user_id)).all())


# ---------------------------------------------------------------- read phase
async def read_handlers(c: ReflexClient, n_cheap: int, n_llm: int, tag: str) -> list[Result]:
    out = []
    out.append(await measure(c, "DashboardState.load_dashboard", f"{DASH}.load_dashboard", {},
                             v_dashboard, n_llm, "/dashboard",
                             note="calls generate_briefing (LLM) on every invocation"))
    out.append(await measure(c, "TransactionsState.load_transactions", f"{TXNS}.load_transactions", {},
                             v_transactions, n_cheap, "/transactions"))
    out.append(await measure(c, "InsightsState.load_insights", f"{INSIGHTS}.load_insights", {},
                             v_insights, n_llm, "/insights",
                             note="refresh_insights: LLM only for new/changed patterns"))
    out.append(await measure(c, "CommitmentsState.load_commitments_page",
                             f"{COMMIT}.load_commitments_page", {}, v_commitments, n_cheap,
                             "/commitments"))
    for r in out:
        r.handler = f"{r.handler}"
    return out
