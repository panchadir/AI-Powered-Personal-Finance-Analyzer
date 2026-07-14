"""Shared profiling harness: synthetic data, query counting, timing.

Runs IN-CONTAINER (piped via `docker compose exec -T app python - < file`), because the
image has no source bind-mount. Writes nothing to the app DB except rows belonging to the
dedicated synthetic user `perfprofile@example.com` -- user_id=2 (the demo user) is never
touched, per coordination with the concurrent e2e-latency agent.
"""
from __future__ import annotations

import json
import random
import statistics
import time
from contextlib import contextmanager
from datetime import date, timedelta
from decimal import Decimal

import reflex as rx
import sqlmodel
from sqlalchemy import event, text
from sqlalchemy.engine import Engine
from sqlmodel import select

from finance_app.models import (
    Commitment,
    CommitmentSuggestion,
    Insight,
    ScoreEvent,
    Transaction as TxnModel,
)
from reflex_local_auth.user import LocalUser

PERF_EMAIL = "perfprofile@example.com"
PERF_PASSWORD = "perfperf1"

# ---------------------------------------------------------------- query counting

_QUERIES: list[str] = []
_COUNTING = False


def _on_cursor(conn, cursor, statement, params, context, executemany):
    if _COUNTING:
        _QUERIES.append(statement)


event.listen(Engine, "after_cursor_execute", _on_cursor)


@contextmanager
def count_queries():
    """Count every SQL statement issued inside the block."""
    global _COUNTING
    _QUERIES.clear()
    _COUNTING = True
    try:
        yield _QUERIES
    finally:
        _COUNTING = False


def summarize_queries(queries: list[str]) -> dict:
    """Group counted statements by their leading verb+table for N+1 diagnosis."""
    norm: dict[str, int] = {}
    for q in queries:
        key = " ".join(q.split())[:90]
        norm[key] = norm.get(key, 0) + 1
    return {
        "total": len(queries),
        "distinct": len(norm),
        "by_statement": sorted(norm.items(), key=lambda kv: -kv[1])[:8],
    }


# ---------------------------------------------------------------- timing

def timeit(fn, *, runs: int = 5, warmup: bool = True) -> dict:
    """Wall-clock a callable. Returns cold (1st call) + warm min/p50/max in ms."""
    t0 = time.perf_counter()
    fn()
    cold_ms = (time.perf_counter() - t0) * 1000

    samples = []
    for _ in range(runs):
        t = time.perf_counter()
        fn()
        samples.append((time.perf_counter() - t) * 1000)

    return {
        "cold_ms": round(cold_ms, 2),
        "warm_min_ms": round(min(samples), 2),
        "warm_p50_ms": round(statistics.median(samples), 2),
        "warm_max_ms": round(max(samples), 2),
        "runs": runs,
    }


# ---------------------------------------------------------------- synthetic data

def get_perf_user(session) -> int:
    user = session.exec(
        sqlmodel.select(LocalUser).where(LocalUser.username == PERF_EMAIL)
    ).first()
    if user is None:
        user = LocalUser(
            username=PERF_EMAIL,
            password_hash=LocalUser.hash_password(PERF_PASSWORD),
            enabled=True,
        )
        session.add(user)
        session.commit()
        session.refresh(user)
    return user.id


_MERCHANTS = [
    ("SWIGGY", "Dining", Decimal("380")),
    ("ZOMATO", "Dining", Decimal("420")),
    ("UBER", "Transport", Decimal("240")),
    ("AMAZON", "Shopping", Decimal("1200")),
    ("BIGBASKET", "Groceries", Decimal("2100")),
    ("STARBUCKS", "Dining", Decimal("310")),
    ("PETROL PUMP", "Transport", Decimal("2000")),
    ("PHARMACY", "Health", Decimal("450")),
]
# recurring subscriptions -- monthly, near-constant (feeds zombie/commitment detectors)
_SUBS = [
    ("NETFLIX", "Subscriptions", Decimal("649"), 12),
    ("SPOTIFY", "Subscriptions", Decimal("119"), 18),
    ("ADOBE CC", "Subscriptions", Decimal("1675"), 22),
]

_HISTORY_MONTHS = 6


def set_transaction_count(session, user_id: int, n: int, *, seed: int = 7) -> int:
    """Make the perf user have exactly ``n`` transactions. Deterministic for a given seed."""
    session.exec(
        text("DELETE FROM transactions WHERE user_id = :u").bindparams(u=user_id)
    )
    session.commit()
    if n == 0:
        return 0

    rng = random.Random(seed)
    end = date(2026, 6, 30)
    start = end - timedelta(days=_HISTORY_MONTHS * 30)
    span_days = (end - start).days

    rows = []
    balance = Decimal("85000")

    # 1. Monthly salary credits (so income detection + payday detectors fire).
    for m in range(_HISTORY_MONTHS):
        d = start + timedelta(days=m * 30 + 1)
        amt = Decimal("75000")
        balance += amt
        rows.append(
            dict(
                date=d.isoformat(),
                description_raw=f"NEFT SALARY CR ACME CORP {d.isoformat()}",
                merchant_normalized="ACME CORP",
                amount=amt,
                direction="credit",
                balance_after=balance,
                category="Income",
                category_source="rule",
                category_confidence=0.99,
            )
        )

    # 2. Monthly recurring subscriptions (zombie / commitment-detector fodder).
    for name, cat, amt, day in _SUBS:
        for m in range(_HISTORY_MONTHS):
            d = start + timedelta(days=m * 30 + day)
            if d > end:
                continue
            balance -= amt
            rows.append(
                dict(
                    date=d.isoformat(),
                    description_raw=f"UPI/{name}/SUBSCRIPTION",
                    merchant_normalized=name,
                    amount=amt,
                    direction="debit",
                    balance_after=balance,
                    category=cat,
                    category_source="rule",
                    category_confidence=0.95,
                )
            )

    # 3. Fill the remainder with ordinary debits spread across the window.
    while len(rows) < n:
        name, cat, base = _MERCHANTS[rng.randrange(len(_MERCHANTS))]
        d = start + timedelta(days=rng.randrange(span_days))
        amt = (base * Decimal(rng.randrange(50, 150)) / Decimal(100)).quantize(Decimal("0.01"))
        balance -= amt
        rows.append(
            dict(
                date=d.isoformat(),
                description_raw=f"UPI/{name}/{rng.randrange(10**9)}",
                merchant_normalized=name,
                amount=amt,
                direction="debit",
                balance_after=balance,
                category=cat,
                category_source="rule",
                category_confidence=0.9,
            )
        )

    rows = rows[:n]
    rows.sort(key=lambda r: r["date"])

    # Recompute balance_after in date order so the closing balance is coherent.
    bal = Decimal("85000")
    for r in rows:
        bal = bal + r["amount"] if r["direction"] == "credit" else bal - r["amount"]
        r["balance_after"] = bal

    from datetime import datetime

    from sqlalchemy import inspect as sa_inspect

    now = datetime.utcnow()
    session.bulk_insert_mappings(
        sa_inspect(TxnModel),
        [dict(r, user_id=user_id, source_file_id=None, reasoning=None, created_at=now) for r in rows],
    )
    session.commit()
    return len(rows)


def ensure_commitments(session, user_id: int) -> None:
    existing = session.exec(
        select(Commitment).where(Commitment.user_id == user_id)
    ).all()
    if existing:
        return
    for name, amt, day, crit in [
        ("Rent", Decimal("22000"), 3, "critical"),
        ("Car Loan EMI", Decimal("6500"), 5, "critical"),
        ("Gym", Decimal("1500"), 20, "flexible"),
    ]:
        session.add(
            Commitment(
                user_id=user_id, name=name, amount=amt, due_day=day, criticality=crit
            )
        )
    session.commit()


def clear_derived(session, user_id: int) -> None:
    """Wipe insights / score events / suggestions for the perf user (repeatable runs)."""
    for table in ("insights", "score_events", "commitment_suggestions"):
        session.exec(
            text(f"DELETE FROM {table} WHERE user_id = :u").bindparams(u=user_id)
        )
    session.commit()


def cleanup(session, user_id: int) -> None:
    clear_derived(session, user_id)
    for table in ("transactions", "commitments"):
        session.exec(
            text(f"DELETE FROM {table} WHERE user_id = :u").bindparams(u=user_id)
        )
    session.commit()


def emit(obj) -> None:
    print("@@JSON@@" + json.dumps(obj, default=str))
