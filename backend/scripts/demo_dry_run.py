#!/usr/bin/env python3
"""Story 8.5 AC2 — Demo dry run: golden-path pipeline guard.

Exercises steps 3–7 of the demo walkthrough as service-layer assertions:
  Step 3: Parse the demo bank statement PDF → PDFParser
  Step 4: Persist transactions into the DB → persist_transactions
  Step 5: Compute Dashboard → assert non-zero STS figure
  Step 6: Run Insights → assert ≥ 3 active insight cards
  Step 7: Copilot data layer → assert spending context is non-empty

Run with:  pytest scripts/demo_dry_run.py -v

Design notes:
- Uses a tmp SQLite DB (no Postgres, no Docker needed).
- Seeds the canonical demo user + data via seed_demo.seed().
- Also uploads the demo PDF to the same user, then adds a small set of
  synthetic zombie-subscription rows so the Insights pass meets its ≥ 3 threshold
  regardless of how much demo-data.json and the demo PDF happen to overlap.
- ANTHROPIC_API_KEY is NOT needed — narration falls back to deterministic stubs
  when the env var is absent, so this test runs fully offline (AD-1).
"""
from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path

import pytest
import sqlmodel

_ROOT = Path(__file__).parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import finance_app.models  # noqa: E402, F401 — registers all tables
from finance_app.models import Transaction as TxnModel
from scripts.seed_demo import _DEMO_EMAIL, seed
from services.ingestion import PDFParser
from services.ingestion.persist import persist_transactions

_PDF = _ROOT / "data" / "OpTransactionHistory10-07-2026_3625 1.pdf"

# Synthetic zombie-subscription transactions added to the dry-run fixture so that
# ≥ 3 insight patterns reliably fire.  Two identical Netflix charges ~30 days apart
# satisfy the ZombieSubscriptionDetector's cadence + amount-equality conditions.
_ZOMBIE_ROWS = [
    {"date": "2026-05-03", "description_raw": "NETFLIX_SUBSCRIPTION", "amount": "499.00", "direction": "debit"},
    {"date": "2026-06-03", "description_raw": "NETFLIX_SUBSCRIPTION", "amount": "499.00", "direction": "debit"},
]


@pytest.fixture(scope="module")
def demo_db(tmp_path_factory):
    """Shared in-module DB: seed → upload PDF → add zombie rows → yield (session, user_id)."""
    db_path = tmp_path_factory.mktemp("dry_run") / "dry_run.db"
    engine = sqlmodel.create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
    )
    sqlmodel.SQLModel.metadata.create_all(engine)

    # Step 3 & 4a: seed canonical demo data
    result = seed(engine=engine)
    user_id = result["user_id"]

    # Step 4b: parse and persist the demo PDF
    assert _PDF.exists(), (
        f"Demo PDF not found at {_PDF}. "
        "Ensure 'data/OpTransactionHistory10-07-2026_3625 1.pdf' is present."
    )
    txns = PDFParser().parse(_PDF)
    with sqlmodel.Session(engine) as session:
        persist_transactions(session, TxnModel, user_id, None, txns)

    # Step 4c: add synthetic zombie-subscription rows (ensures ≥ 3 insight patterns fire)
    with sqlmodel.Session(engine) as session:
        for row in _ZOMBIE_ROWS:
            session.add(TxnModel(  # type: ignore[call-arg]
                user_id=user_id,
                date=row["date"],
                description_raw=row["description_raw"],
                amount=Decimal(row["amount"]),
                direction=row["direction"],
            ))
        session.commit()

    yield engine, user_id


# ---------------------------------------------------------------------------
# Step 5: Dashboard — non-zero STS
# ---------------------------------------------------------------------------

def test_step5_dashboard_sts_is_nonzero(demo_db):
    """Dashboard hero card must show a non-zero Safe-to-Spend figure after upload."""
    from finance_app.state.engine_bridge import compute_dashboard

    engine, user_id = demo_db
    with sqlmodel.Session(engine) as session:
        data = compute_dashboard(session, user_id)

    assert data.has_data, "Dashboard reports no data — transaction upload may have failed."
    assert data.evidence.safe_to_spend_today > 0, (
        f"STS is {data.evidence.safe_to_spend_today} — expected a positive non-zero figure "
        "after uploading the demo statement."
    )


def test_step5_dashboard_transaction_count(demo_db):
    """Dashboard should reflect combined seed + PDF transaction count."""
    from finance_app.state.engine_bridge import compute_dashboard

    engine, user_id = demo_db
    with sqlmodel.Session(engine) as session:
        data = compute_dashboard(session, user_id)

    assert data.transaction_count >= 65, (
        f"Expected at least 65 transactions (PDF alone), got {data.transaction_count}."
    )


# ---------------------------------------------------------------------------
# Step 6: Insights — ≥ 3 active cards
# ---------------------------------------------------------------------------

def test_step6_insights_at_least_3_cards(demo_db):
    """Insights page must show ≥ 3 active insight cards after the golden-path upload."""
    from finance_app.state.insights_bridge import refresh_insights

    engine, user_id = demo_db
    with sqlmodel.Session(engine) as session:
        data = refresh_insights(session, user_id)

    active_count = len(data.active)
    assert active_count >= 3, (
        f"Expected ≥ 3 active insights after demo upload, got {active_count}. "
        f"Active patterns: {[i.pattern_name for i in data.active]}"
    )


def test_step6_insights_have_narration(demo_db):
    """Each active insight must have a non-empty observation and action_suggestion.

    The narration fallback fires offline when ANTHROPIC_API_KEY is absent (AD-1),
    so this assertion holds without any LLM call.
    """
    from finance_app.state.insights_bridge import refresh_insights

    engine, user_id = demo_db
    with sqlmodel.Session(engine) as session:
        data = refresh_insights(session, user_id)

    for insight in data.active:
        assert insight.observation, f"Insight '{insight.pattern_name}' has no observation."
        assert insight.action_suggestion, f"Insight '{insight.pattern_name}' has no action suggestion."


# ---------------------------------------------------------------------------
# Step 7: Copilot data layer — spending context is non-empty
# ---------------------------------------------------------------------------

def test_step7_copilot_data_layer_non_empty(demo_db):
    """Copilot's input (load_transactions) must return non-empty data so tool calls work."""
    from finance_app.state.engine_bridge import load_transactions

    engine, user_id = demo_db
    with sqlmodel.Session(engine) as session:
        txns = load_transactions(session, user_id)

    assert txns, "Copilot data layer has no transactions — tool calls would return empty context."


def test_step7_spending_by_category_is_non_empty(demo_db):
    """spending_by_category must return at least one slice so Copilot can answer spend questions."""
    from finance_app.state.engine_bridge import load_transactions
    from services.analytics.spending import spending_by_category

    engine, user_id = demo_db
    with sqlmodel.Session(engine) as session:
        txns = load_transactions(session, user_id)

    slices = spending_by_category(txns)
    assert slices, "spending_by_category returned no slices — Copilot cannot answer spend queries."


# ---------------------------------------------------------------------------
# Bonus: demo user credentials exist and are navigable
# ---------------------------------------------------------------------------

def test_demo_user_credentials_present(demo_db):
    """The canonical demo user must exist with the expected email."""
    from reflex_local_auth.user import LocalUser

    engine, user_id = demo_db
    with sqlmodel.Session(engine) as session:
        user = session.exec(
            sqlmodel.select(LocalUser).where(LocalUser.username == _DEMO_EMAIL)
        ).first()

    assert user is not None, f"Demo user '{_DEMO_EMAIL}' not found."
    assert user.enabled, "Demo user is disabled — login will fail."
    assert user.id == user_id


if __name__ == "__main__":
    import subprocess
    raise SystemExit(subprocess.call(["pytest", __file__, "-v"]))
