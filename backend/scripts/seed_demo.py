#!/usr/bin/env python3
"""Seed the canonical demo user and demo dataset.

Usage:
    python scripts/seed_demo.py            # create/update demo data (idempotent)
    python scripts/seed_demo.py --reset    # wipe demo user's data then re-seed

DATABASE_URL is read from the environment (falls back to a local SQLite file so the
script and its tests work without Postgres).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from decimal import Decimal
from pathlib import Path

import sqlmodel

# Ensure the project root is on sys.path when run as a script.
_ROOT = Path(__file__).parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import finance_app.models  # noqa: E402, F401 — registers all tables with SQLModel metadata
from finance_app.models import (
    ChatMessage,
    Commitment,
    CommitmentSuggestion,
    Insight,
    MerchantRule,
    ScoreEvent,
    Transaction as TxnModel,
    UploadedFile,
)
from reflex_local_auth.user import LocalUser

_DEMO_EMAIL = "demo@example.com"
_DEMO_PASSWORD = "demodemo1"
_DATA_FILE = _ROOT / "data" / "demo-data.json"

_DEMO_COMMITMENTS = [
    {"name": "Car Loan EMI",  "amount": Decimal("6500.00"), "due_day": 5,  "criticality": "critical"},
    {"name": "HDFC EMI",      "amount": Decimal("8500.00"), "due_day": 15, "criticality": "critical"},
]


def _get_engine() -> sqlmodel.Engine:
    url = os.environ.get("DATABASE_URL") or f"sqlite:///{_ROOT / 'finance_local.db'}"
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return sqlmodel.create_engine(url, connect_args=connect_args)


def _ensure_schema(engine: sqlmodel.Engine) -> None:
    sqlmodel.SQLModel.metadata.create_all(engine)


def _get_or_create_user(session: sqlmodel.Session) -> LocalUser:
    existing = session.exec(
        sqlmodel.select(LocalUser).where(LocalUser.username == _DEMO_EMAIL)
    ).first()
    if existing is not None:
        return existing
    user = LocalUser(  # type: ignore[call-arg]
        username=_DEMO_EMAIL,
        password_hash=LocalUser.hash_password(_DEMO_PASSWORD),
        enabled=True,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def _seed_transactions(session: sqlmodel.Session, user_id: int) -> int:
    """Insert demo transactions if none exist for this user. Returns count inserted."""
    existing_count = session.exec(
        sqlmodel.select(sqlmodel.func.count()).select_from(TxnModel).where(
            TxnModel.user_id == user_id
        )
    ).one()
    if existing_count > 0:
        return 0

    rows = json.loads(_DATA_FILE.read_text(encoding="utf-8"))
    for row in rows:
        session.add(TxnModel(  # type: ignore[call-arg]
            user_id=user_id,
            date=row["date"],
            description_raw=row["description_raw"],
            amount=Decimal(row["amount"]),
            direction=row["direction"],
        ))
    session.commit()
    return len(rows)


def _seed_commitments(session: sqlmodel.Session, user_id: int) -> int:
    """Insert demo commitments if none exist for this user. Returns count inserted."""
    existing_count = session.exec(
        sqlmodel.select(sqlmodel.func.count()).select_from(Commitment).where(
            Commitment.user_id == user_id
        )
    ).one()
    if existing_count > 0:
        return 0

    for c in _DEMO_COMMITMENTS:
        session.add(Commitment(  # type: ignore[call-arg]
            user_id=user_id,
            name=c["name"],
            amount=c["amount"],
            due_day=c["due_day"],
            criticality=c["criticality"],
        ))
    session.commit()
    return len(_DEMO_COMMITMENTS)


def _reset_user_data(session: sqlmodel.Session, user_id: int) -> None:
    """Delete all user-scoped rows so seed can re-run cleanly."""
    for model in (
        TxnModel, Commitment, CommitmentSuggestion, ScoreEvent,
        Insight, ChatMessage, MerchantRule, UploadedFile,
    ):
        rows = session.exec(sqlmodel.select(model).where(model.user_id == user_id)).all()  # type: ignore[attr-defined]
        for row in rows:
            session.delete(row)
    session.commit()


def seed(*, reset: bool = False, engine: sqlmodel.Engine | None = None) -> dict:
    """Run the full seed sequence. Returns a summary dict with counts."""
    if engine is None:
        engine = _get_engine()
    _ensure_schema(engine)

    with sqlmodel.Session(engine) as session:
        user = _get_or_create_user(session)
        user_id = user.id

        if reset:
            _reset_user_data(session, user_id)

        txn_count = _seed_transactions(session, user_id)
        commitment_count = _seed_commitments(session, user_id)

    return {
        "user_id": user_id,
        "transactions_inserted": txn_count,
        "commitments_inserted": commitment_count,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed the AI Finance demo dataset.")
    parser.add_argument(
        "--reset", action="store_true",
        help="Wipe the demo user's data before seeding (for a clean demo reset).",
    )
    args = parser.parse_args()

    result = seed(reset=args.reset)
    action = "reset and re-seeded" if args.reset else "seeded"
    print(
        f"Demo data {action}: "
        f"{result['transactions_inserted']} transactions, "
        f"{result['commitments_inserted']} commitments "
        f"(user_id={result['user_id']})."
    )


if __name__ == "__main__":
    main()
