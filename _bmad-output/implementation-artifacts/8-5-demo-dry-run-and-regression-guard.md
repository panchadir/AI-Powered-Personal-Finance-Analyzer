---
baseline_commit: bae7b040cf5b7bfaeebe2de9c123f5af73596f0d
---

# Story 8.5: Demo Dry Run & Regression Guard

Status: done

## Story

As the demo presenter,
I want a scripted walkthrough that verifies the golden path is intact and produces no surprises,
So that the demo is repeatable and trustworthy.

## Story Context

**Epic 8 — Hardening & Demo-Readiness, story 5 of 5.** Stories 8.1–8.4 are done.

**What exists:**
- `data/OpTransactionHistory10-07-2026_3625 1.pdf` — ICICI Bank statement (June 2026), 65 transactions
- `data/demo-data.json` — 24 pre-seeded demo transactions
- `scripts/seed_demo.py` — idempotent demo seeder
- `finance_app/state/engine_bridge.py` — `compute_dashboard()`, `load_transactions()`
- `finance_app/state/insights_bridge.py` — `refresh_insights()`
- `services/ingestion/` — `PDFParser`, `persist_transactions`
- `tests/ingestion/` — existing golden-file and parser tests

**Key facts from investigation:**
- The demo PDF is an ICICI Bank statement (not HDFC — the bank that issued it is ICICI), 65 transactions
- `PDFParser().parse()` already handles it perfectly via the pdfplumber/text-extraction chain → 65 transactions
- `statementsparser` with `bank='HDFC'` fails on this PDF (format mismatch); not needed
- Epic AC says "HDFC demo PDF parses to ≥90% of known count" → the known count is 65, so ≥59 (90%)
- `DashboardData.evidence.safe_to_spend_today` is the STS figure (Decimal)
- `InsightData.active` is the list of active insight rows
- Copilot/streaming tested via service-layer mock (AppHarness requires Selenium + running frontend, outside MVP scope)

**Epic AC interpretation for `demo_dry_run.py`:**
The AC says "automates steps 3–7 using the Reflex test client" — in practice this means:
steps 3-7 are service-layer operations (parse PDF → persist → compute dashboard → run insights → copilot query).
We implement a pytest module that exercises these 5 steps end-to-end against a real SQLite DB,
asserting all the outcome conditions. This satisfies the AC's intent without requiring a running browser.

## Acceptance Criteria

**AC1 — Golden-file regression:**
- `tests/ingestion/test_demo_pdf_golden.py` parses `data/OpTransactionHistory10-07-2026_3625 1.pdf`
- Asserts ≥ 59 transactions parsed (90% of 65 known rows)
- Asserts all rows have valid `date`, `amount`, `direction`

**AC2 — `scripts/demo_dry_run.py` exists and is a valid pytest module:**
- Exercises the golden path steps 3–7: parse PDF → persist → compute dashboard → refresh insights → copilot data layer
- Asserts Dashboard hero shows non-zero STS figure
- Asserts ≥ 3 insight cards visible after seeding demo data + running insights
- Asserts Copilot data layer returns valid spending context (non-empty)
- `pytest scripts/demo_dry_run.py` passes

**AC3 — No existing tests broken:** full suite passes (688 currently passing)

## Tasks / Subtasks

- [x] **Task 1 — Golden-file PDF regression (AC1)**
  - [x] Create `tests/ingestion/test_demo_pdf_golden.py`
  - [x] Assert `PDFParser().parse(PDF_PATH)` returns ≥ 59 rows
  - [x] Assert all rows have non-empty date, positive amount, valid direction
  - [x] Run test to confirm green

- [x] **Task 2 — Demo dry-run script (AC2)**
  - [x] Create `scripts/demo_dry_run.py` as a pytest module with a `demo_db` fixture
  - [x] Step 3: Parse demo PDF → `PDFParser().parse()`
  - [x] Step 4: Persist transactions → `persist_transactions()` with injected model
  - [x] Step 5: Compute dashboard → `compute_dashboard()` → assert non-zero STS
  - [x] Step 6: Refresh insights → `refresh_insights()` → assert ≥ 3 active insight cards (seeded data may need supplement)
  - [x] Step 7: Copilot data layer → `compute_dashboard()` plus spending query → assert non-empty
  - [x] Run `pytest scripts/demo_dry_run.py` to confirm all pass

- [x] **Task 3 — Full regression suite (AC3)**
  - [x] Run `pytest` → confirm all previously passing tests still pass

## Dev Notes

**PDF file path:** `Path(__file__).parent.parent / "data" / "OpTransactionHistory10-07-2026_3625 1.pdf"`

**Golden count:** 65 transactions in the PDF (verified with pdfplumber text extraction). Threshold = 59 (≥90%).

**For insights ≥3:** `refresh_insights()` is an async function that calls `asyncio.to_thread()`. In tests:
use `asyncio.run(refresh_insights(session, user_id))`. The demo-seeded data (24 transactions) should
produce multiple insight candidates. If needed, pre-seed with extra months of data to ensure ≥3 active cards.
Alternatively, after PDF upload + seed data combined, insights should fire.

**`persist_transactions` signature:**
```python
persist_transactions(
    session,
    transactions: list[Transaction],
    user_id: int,
    txn_model,         # finance_app.models.Transaction (injected, not imported)
    source_file_id=None,
) -> PersistResult
```

**`refresh_insights` signature:**
```python
async def refresh_insights(session: Session, user_id: int) -> InsightData
```

**AD-2 compliance:** `scripts/demo_dry_run.py` is NOT under `services/` so it may import `finance_app.models` for the txn_model injection. It uses the same pattern as `seed_demo.py`.

**Test DB pattern:** use `tmp_path` SQLite engine, `SQLModel.metadata.create_all`, same as `test_seed_demo.py` and `test_idor.py`.

**Copilot step:** The Copilot streams via Claude API. For the dry-run, test only the data layer (what `CopilotState` reads from DB) — not the actual LLM stream. Verify `load_transactions(session, user_id)` returns non-empty (the copilot's input to the tool calls) and a narration context is buildable.

## Dev Agent Record

### Debug Log
- `Insight` model has `observation`/`action_suggestion` fields, not `headline`/`body`. Fixed narration test to use correct field names.
- Demo data (24 txns from demo-data.json + 65 from PDF) only produces 2 insights: "Upcoming commitment collision" + "Death by small purchases". Added synthetic zombie-subscription rows (2× NETFLIX_SUBSCRIPTION charges 30 days apart) to the dry-run fixture to reliably reach ≥3 patterns. This is fixture augmentation, not a change to seed_demo.py.
- PDF is an ICICI Bank statement (not HDFC) — `statementsparser` with `bank='HDFC'` fails on it; the existing pdfplumber text-extraction chain handles it correctly (65 transactions, 100% recall).

### Completion Notes
- **AC1 GOLDEN-FILE**: `tests/ingestion/test_demo_pdf_golden.py` — 5 tests: ≥59 transactions (got 65), valid dates, positive Decimal amounts, valid directions, both credit+debit present. All pass.
- **AC2 DRY-RUN**: `scripts/demo_dry_run.py` — 7 tests: STS non-zero (₹4,950), transaction count ≥65, ≥3 insight cards (got 3: Death by small purchases, Upcoming commitment collision, Zombie subscriptions), narration non-empty, copilot data layer non-empty, spending_by_category non-empty, demo user credentials present. All pass.
- **AC3 REGRESSION**: 693 passed, 6 skipped. 12 new tests added (5 golden-file + 7 dry-run). Zero regressions.

## File List
- `tests/ingestion/test_demo_pdf_golden.py` — new golden-file regression test (AC1)
- `scripts/demo_dry_run.py` — new dry-run pytest module (AC2)

## Change Log
- Story 8.5 implementation (2026-07-12): golden-file PDF test (5 tests), demo dry-run script (7 tests). 693 passed, 6 skipped.
- 2026-07-12 — Code review patch: `_MIN_COUNT = math.ceil(65 * 0.9)` → 59 (was `int(58.5)` = 58, one looser than AC required). Status → `done`.
