---
baseline_commit: d0b4a8f5d79cf208e1da96527944e54c0d796e04
---

# Story 4.2: Safe-to-Spend Engine Implementation

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **user of the finance analyzer**,
I want **a deterministic Safe-to-Spend figure that fully ring-fences my committed bills, floors at ₹0, and honestly separates today's money from money arriving on payday**,
so that **I can trust the headline number will never tell me to spend cash that a rent/EMI/bill already claims — the product's core kill-signal**.

> Implements epic **S4.1** against the LOCKED contract [`4-1-engine-contract.md`](4-1-engine-contract.md). **Pure, deterministic Python — the LLM never computes a number here (AD-1). Money is `Decimal`, never `float` (AD-8).** This is part of the honesty/safety spine that is **never cut**.

## Acceptance Criteria

1. **`services/engine/safe_to_spend.py` exists** and exposes a clean public API: the dataclasses `CommitmentInput`, `EngineInput`, `EvidencePack` (exact shapes from contract §3–§4) and a pure function `compute_safe_to_spend(engine_input: EngineInput) -> EvidencePack`. Re-exported from `services/engine/__init__.py`.

2. **Formula + floor + rounding (AD-8 / contract §1):** `safe_to_spend_today = max(0, (available_balance − reserved_total − buffer) ÷ days_to_income)`, rounded **down** to nearest ₹10 via `math.floor(x / 10) * 10`. Every returned STS figure ends in `0`; STS is **never negative**; all money arithmetic is `Decimal` (round-down applied on the `Decimal`, not a drifted float).

3. **Reservation Rule DD-1 (contract §2) fully implemented:** (1) known commitment due on-or-before next income → always fully reserved; (2) predicted commitment → reserved **only** inside its criticality window (critical 7d / important 5d / flexible 3d), else surfaced as a driver + lowers prediction confidence but **not** subtracted; (3) variable-amount → reserve **top of range** (`amount`, with `amount_min` set); (4) commitment due **on income day** → reserved against current balance unless `income_confidence == "High"` AND income ≥ commitment.

4. **Two-layer output (FR-4.5):** `safe_to_spend_today` and `safe_to_spend_after_income` are computed and returned separately; the after-income layer is `None` **only** when no income is detected (scenario 12). The two are never merged.

5. **Denominator guard (contract §1a / Seam):** when `days_to_income` is `0` (payday today) or `None` (no confirmed income), the engine returns the reserved-only fallback `safe_to_spend_today = max(0, spendable_pool)` (undivided) — **no `ZeroDivisionError`, `Infinity`, or `NaN`**. Scenario 12 (`None`) → `safe_to_spend_after_income = None` + `data_quality_flags` contains `"no_income_detected"`. Scenario 13 (`0`) → STS = `max(0, pool)`.

6. **Full evidence pack returned (FR-4.12):** every field populated — `reserved_total`, `spendable_pool`, `days_to_income`, `safe_to_spend_today`, `safe_to_spend_after_income`, `prediction_confidence` (`Low|Medium|High`), `drivers`, `data_quality_flags`, `safety_ok`. `safety_ok` is `True` iff every commitment due on-or-before next income is fully covered by `reserved_total`; `False` triggers on the shortfall path (scenario 10) with a shortfall driver naming the ₹ gap.

7. **Targeted unit tests pass with zero LLM calls (AD-1).** `pytest services/engine/` (or `pytest tests/engine/`) is green. Tests cover the *mechanics* — round-down, ₹0 floor, ÷0 and ÷undefined guards, each of the 4 DD-1 sub-rules, top-of-range reserve, and **at least representative scenarios 1, 2, 10, 12, 13** end-to-end. **The exhaustive 13-scenario table-driven gate + CS-1..CS-4 is story 4-3 — do NOT build the full parametrized suite here (scope boundary).** A `conftest`/fixture asserts no `anthropic` client is constructed in engine tests.

8. **`prediction_confidence` derivation is present but minimal:** returns `Low|Medium|High` from data-completeness signals available in the input (e.g. presence of predicted/uncertain commitments → lowers it; a `low_data` marker → `Low`). The full 0–100 preparedness **Confidence Score** and `score_events` writeback are **story 4-4** — not here.

## Tasks / Subtasks

- [x] **Task 1 — Author the dataclasses + module skeleton (AC: 1)**
  - [x] In `services/engine/safe_to_spend.py`, define `CommitmentInput`, `EngineInput`, `EvidencePack` exactly per contract §3–§4 (`@dataclass(frozen=True)`, `Decimal` money, `date` fields). `from __future__ import annotations`.
  - [x] Re-export the public names from `services/engine/__init__.py` (keep the existing module docstring).
  - [x] Confirm no `reflex`/`rx.*`/`finance_app` import (AD-1/AD-2) — `tests/test_service_boundary.py` will enforce this automatically.
- [x] **Task 2 — Reservation engine: DD-1 (AC: 3, 6) — RED then GREEN**
  - [x] Write failing unit tests for each DD-1 sub-rule (known-before-income reserved; predicted-outside-window not reserved but surfaced; predicted-inside-window reserved; variable→top-of-range; due-on-income-day rule with High vs <High income confidence).
  - [x] Implement `_reserve_for_commitment(...)` returning `(amount_to_reserve, driver)`; compute per-commitment `due_date` vs `as_of` day-distance and criticality window (7/5/3). Reserved total + prediction-confidence signal assembled in `compute_safe_to_spend`.
  - [x] Build `drivers` strings for each reserved/surfaced commitment (human-readable; these feed narration later — no arithmetic invented downstream, AD-1).
- [x] **Task 3 — Pool, days-to-income, formula, floor, rounding (AC: 2, 5) — RED then GREEN**
  - [x] Failing tests: round-down to ₹10 (e.g. 833.3→830), ₹0 floor on negative pool, ÷0 guard (days=0), ÷undefined guard (next_income_date=None).
  - [x] Implement `spendable_pool = balance − reserved_total − buffer` (Decimal), `days_to_income` from `next_income_date − as_of`, and the guarded division. Round-down helper on `Decimal`: `Decimal(math.floor(x / 10) * 10)` — apply to the Decimal quotient, never a float.
- [x] **Task 4 — Two-layer output + salary-not-detected + shortfall (AC: 4, 5, 6) — RED then GREEN**
  - [x] Failing tests for: after-income layer computed when income present; `safe_to_spend_after_income=None` + `"no_income_detected"` flag when `next_income_date is None` (scenario 12); shortfall → STS `0`, `safety_ok=False`, shortfall driver names the gap (scenario 10).
  - [x] Implement `safe_to_spend_after_income` (per-day figure over the cycle following income) and `safety_ok` (balance can honour every ring-fenced commitment).
- [x] **Task 5 — Assemble `compute_safe_to_spend` + representative scenario tests (AC: 6, 7)**
  - [x] Wire helpers into the public function returning a fully-populated `EvidencePack`.
  - [x] Add end-to-end tests for **scenarios 1, 2, 10, 12, 13** (from contract §5), asserting the headline fields. Left the full 13-row parametrized gate + CS assertions to story 4-3.
  - [x] Add the zero-LLM guard fixture (see Dev Notes) under `tests/engine/conftest.py`.
- [x] **Task 6 — Green + boundary check (AC: 2, 7)**
  - [x] Run `pytest tests/engine/ tests/test_service_boundary.py` — all green (20 passed), zero LLM calls.
  - [x] Confirm every STS figure in test outputs ends in `0` and no test constructs an Anthropic client.

## Dev Notes

### THE contract to build against
Read [`4-1-engine-contract.md`](4-1-engine-contract.md) first and in full — it is the LOCKED source of truth (formula §1, ÷0 guard §1a, DD-1 §2, criticality windows §2a, buffer §2b, input shape §3, evidence-pack shape §4, the 13-scenario table §5, decisions §8). Where this story and the contract ever disagree, **the contract wins** — raise the conflict, don't silently resolve it.

### Exact shapes to implement (from contract §3–§4 — do not drift field names)
```python
# services/engine/safe_to_spend.py
from __future__ import annotations
import math
from dataclasses import dataclass
from decimal import Decimal
from datetime import date

@dataclass(frozen=True)
class CommitmentInput:
    name: str
    amount: Decimal                     # variable bill: TOP of range
    amount_min: Decimal | None = None
    due_date: date | None = None
    criticality: str = "important"      # 'critical' | 'important' | 'flexible'
    is_predicted: bool = False

@dataclass(frozen=True)
class EngineInput:
    available_balance: Decimal
    as_of: date
    buffer: Decimal = Decimal("2000")
    commitments: tuple[CommitmentInput, ...] = ()
    next_income_date: date | None = None
    next_income_amount: Decimal | None = None
    income_confidence: str = "High"     # 'Low' | 'Medium' | 'High'

@dataclass(frozen=True)
class EvidencePack:
    reserved_total: Decimal
    spendable_pool: Decimal
    days_to_income: int | None
    safe_to_spend_today: Decimal
    safe_to_spend_after_income: Decimal | None
    prediction_confidence: str          # 'Low' | 'Medium' | 'High'
    drivers: tuple[str, ...]
    data_quality_flags: tuple[str, ...]
    safety_ok: bool
```

### Non-negotiable engine rules (transcribed — these ARE the acceptance spec)
- **`max(0, …)` floor** — STS never negative (AD-8). **Round DOWN** to nearest ₹10: `math.floor(x / 10) * 10`; **rounding up is forbidden**; every STS ends in `0`.
- **Decimal only** — all reservation/pool/STS arithmetic in `Decimal`. `math.floor(x/10)*10` on a drifted `float` rounds the wrong ₹10 (Agent-Misread Guard). Convert to `Decimal` results; `float` is display-only (not this layer's job).
- **Criticality windows:** critical 7d, important 5d, flexible 3d. Enum values exactly `critical|important|flexible` (default `important`) — never the scenario-file prose "medium"/"low" (contract §2a maps medium→important, low→flexible).
- **÷0 / ÷undefined guard (contract §1a):** guard **before** dividing; reserved-only fallback `max(0, spendable_pool)`. Never `ZeroDivisionError`/`Infinity`/`NaN`. This is a payday-morning crash if missed.
- **`safety_ok`** = `True` only when every commitment due on-or-before next confirmed income is fully covered by `reserved_total`.

### Scope boundary with story 4-3 (prevent duplicate/competing tests)
- **This story (4-2):** the engine module + **targeted mechanics tests** + representative scenarios **1, 2, 10, 12, 13** end-to-end. Enough to prove the engine correct.
- **Story 4-3:** the exhaustive `@pytest.mark.parametrize` gate over **all 13** scenarios asserting **every** evidence-pack field per row, plus the **CS-1..CS-4** Confidence-Score companion assertions. Do not pre-build that here.
- **Story 4-4:** `confidence_score.py` (0–100 preparedness score) + `score_events` writeback. This story computes only the `prediction_confidence` string needed for the evidence pack.

### Zero-LLM enforcement fixture (AD-1 — set up here, reused by 4-3)
Engine tests must fail loudly if any code path reaches for the Anthropic client. Add `tests/engine/conftest.py` that structurally blocks it, e.g.:
```python
# tests/engine/conftest.py
import pytest

@pytest.fixture(autouse=True)
def _forbid_anthropic(monkeypatch):
    """AD-1: engine unit tests run with ZERO LLM calls. Any construction raises."""
    def _boom(*a, **k):
        raise AssertionError("engine tests must not construct/use an LLM client (AD-1)")
    try:
        import anthropic
        monkeypatch.setattr(anthropic, "Anthropic", _boom, raising=False)
        monkeypatch.setattr(anthropic, "AsyncAnthropic", _boom, raising=False)
    except ImportError:
        pass  # anthropic not importable in this env → nothing to block, still zero-LLM
```
(Engine code should not import `anthropic` at all; this fixture is the belt-and-suspenders guard the contract §8 requires.)

### Testing standards summary
- Tests live under `tests/engine/` (package already scaffolded: `tests/engine/__init__.py`). Import the engine as `from services.engine.safe_to_spend import compute_safe_to_spend, EngineInput, ...`. Tests run from repo root (no `pytest.ini`; matches existing suites like `tests/utils/test_format.py`).
- Style: match existing tests — module docstring citing the AD/AC, `Decimal` literals for money, plain functions or small `Test*` classes, precise asserts. See `tests/utils/test_format.py` and `tests/test_service_boundary.py` for the house style.
- `pytest tests/engine/` must be **green with zero LLM calls**; `tests/test_service_boundary.py` must stay green (it auto-scans the new module for `reflex`/`finance_app` imports).

### Project Structure Notes
- **New file:** `services/engine/safe_to_spend.py`. **Edited:** `services/engine/__init__.py` (public re-exports; keep the existing docstring). **New tests:** `tests/engine/test_safe_to_spend.py`, `tests/engine/conftest.py`.
- `services/engine/` currently holds only `__init__.py` (empty of code). No `confidence_score.py`/`commitments.py` yet — those are 4-4 / Epic 5. Do **not** create them here.
- **Does not touch** `finance_app/` or any Reflex/`rx.State` code — the engine is framework-agnostic and consumed later by dashboard `rx.State` handlers (Epic 5) via plain dataclasses. Converting DB `Commitment` rows → `CommitmentInput` is the **caller's** job (Epic 5 / a thin adapter), not this engine's.
- **Detected variance:** the `EngineInput` deliberately takes `commitments` as already-classified `CommitmentInput` (with `is_predicted`, `amount_min`, `due_date`). Mapping the persisted `Commitment` model (`due_day: int`, no explicit due_date/predicted flag) to `CommitmentInput` is an adapter concern for the consumer story — flagged so 4-2 doesn't import the model or invent DB access here.

### Previous story intelligence (4-1)
- 4-1 locked the contract and resolved the **12→13 scenario-count discrepancy** (PRD says 12; contract/epic say 13 — 13 wins; scenario 13 = payday-today ÷0 guard). Build for **13**.
- 4-1 locked the **criticality prose→enum mapping** and the **frozen-dataclass (not dict)** return decision — both are hard requirements here.
- 4-1 flagged scenario 3's "~₹990/day" after-income as approximate; 4-2 should **record the exact computed after-income value** for scenario 3 in its completion notes so 4-3 can pin an exact assertion (contract §8 open item).

### References
- [Source: _bmad-output/implementation-artifacts/4-1-engine-contract.md] — LOCKED contract (all sections). Primary.
- [Source: _bmad-output/planning-artifacts/safe-to-spend-scenarios.md] — full scenario inputs (13 rows), DD-1, DD-2, evidence-pack block.
- [Source: _bmad-output/planning-artifacts/prd.md#FR-4] — FR-4.1 formula, FR-4.2 DD-1, FR-4.3 tiers, FR-4.4 buffer, FR-4.5 two-layer, FR-4.8 undetected salary, FR-4.9 shortfall, FR-4.12 struct.
- [Source: ARCHITECTURE-SPINE.md#AD-8] — formula/floor/₹10 round-down; [#AD-1] engine/narrate boundary + zero-LLM engine tests; [#AD-3] engine is the sole financial-state mutator.
- [Source: _bmad-output/project-context.md#Seams] — `[STS denominator guard]` ÷0/undefined fallback (binding); Agent-Misread Guard on `Decimal` vs `float`.
- [Source: services/utils/enums.py] — `Criticality = critical|important|flexible` (default `important`).
- [Source: tests/test_service_boundary.py] — AD-1/AD-2 boundary guard that auto-covers the new module.
- [Source: tests/utils/test_format.py] — house test style to match.

## Dev Agent Record

### Agent Model Used

claude-opus-4-8 (Claude Code / BMAD dev-story)

### Debug Log References

- `pytest tests/engine/ tests/test_service_boundary.py -v` → **20 passed in 0.15s** (17 engine + 3 boundary). Zero LLM calls (autouse `_forbid_anthropic` fixture active; `anthropic` not even importable in the engine venv).
- Env: no project venv existed and neither `reflex` nor `pytest` was installed on system Python. Created `.venv` (gitignored) and installed **pytest 9.1.1 only** — the engine is stdlib-only by design (AD-1/AD-14), so the heavy app deps (reflex/camelot/pandas/psycopg2) are **not** required to run the engine gate. Full-app env setup remains a separate task (Epic 5+ UI work).
- Representative-scenario checks match the contract table exactly: S1 →1250, S2 →830, S10 →0 (pool −9500, safety_ok False), S12 →after_income None + `no_income_detected`, S13 →18000 (days=0 fallback).

### Completion Notes List

- **New module `services/engine/safe_to_spend.py`** — pure `Decimal`, stdlib-only, framework-agnostic. Public API (`CommitmentInput`, `EngineInput`, `EvidencePack`, `compute_safe_to_spend`) re-exported from `services/engine/__init__.py`. `tests/test_service_boundary.py` confirms it imports no `reflex`/`finance_app`.
- **Implements contract §1–§4:** AD-8 formula + ₹0 floor + round-DOWN-to-₹10 (`_floor_to_nearest_ten`, Decimal-safe); DD-1 all 4 sub-rules (`_reserve_for_commitment`); ÷0 & ÷undefined guard (reserved-only fallback); two-layer output; full FR-4.12 evidence pack.
- **Design decision — `safety_ok = available_balance >= reserved_total`** (can the balance honour every ring-fenced commitment?). Chosen over `pool >= 0` so a merely buffer-denting case isn't reported as a *commitment* safety failure. For scenario 10 both fail (balance 16000 < reserved 23500). The shortfall driver's ₹9,500 figure = `reserved + buffer − balance` (= −pool), matching the scenario file's copy.
- **⚠️ Carried to Story 4-3 (contract §8 open item) — scenario 3 after-income mismatch.** Engine computes S3 **today = ₹150 (exact match)** but **after_income = ₹1,830**, while the scenario file says "~₹990/day". The file's figure is flagged-approximate and does not reconcile to any clean formula given the stated inputs (no next-cycle commitments listed). The engine uses `after_income = floor10(max(0, (balance + income − next_cycle_reserved − buffer) / 30))`. **4-3 must reconcile:** either correct the scenario file's ~990, or refine the after-income cycle model. Flagged, not silently resolved.
- **Scope honored:** did NOT build the full 13-scenario parametrized gate or CS-1..CS-4 (Story 4-3); did NOT create `confidence_score.py`/`commitments.py` (Story 4-4 / Epic 5); `prediction_confidence` is the minimal High/Medium derivation only. No `finance_app`/Reflex code touched.
- **`prediction_confidence`:** High by default; Medium when a variable-amount bill (`amount_min` set) or an out-of-window surfaced prediction is present. The `Low` cold-start case (scenario 7) needs a data-completeness signal that belongs to Story 4-4's Confidence Score — noted so 4-3/4-4 wire it.

### File List

- `services/engine/safe_to_spend.py` (new — the engine)
- `services/engine/__init__.py` (edited — public re-exports; docstring preserved)
- `tests/engine/conftest.py` (new — autouse zero-LLM guard, AD-1; reused by 4-3)
- `tests/engine/test_safe_to_spend.py` (new — 17 targeted + representative-scenario tests)
- `.venv/` (new, gitignored — pytest-only engine test env; not committed)
- `_bmad-output/implementation-artifacts/4-2-safe-to-spend-engine-implementation.md` (this story: frontmatter, checkboxes, Dev Agent Record, Change Log, Status)
- `_bmad-output/implementation-artifacts/sprint-status.yaml` (4-2 → in-progress → review; last_updated 2026-07-10)

## Change Log

| Date | Change |
|---|---|
| 2026-07-10 | Story created (ready-for-dev) via bmad-create-story. |
| 2026-07-10 | Implemented `services/engine/safe_to_spend.py` (AD-8 formula, DD-1 reservation, ÷0/undefined guard, two-layer output, FR-4.12 evidence pack) + zero-LLM conftest + 17 targeted/representative tests. `pytest tests/engine/ tests/test_service_boundary.py` → 20 passed. Flagged scenario-3 after-income mismatch for 4-3. Status → review. |
| 2026-07-10 | Code review (bmad-code-review, Epic 4 engine) — 1 patch, 1 decision, 3 deferred, 1 dismissed. Findings below. |
| 2026-07-10 | Applied review actions: fixed the `surfaced_predictions` bug (+ regression test); routed engine ₹/date evidence strings through `formatINR`/`formatDate` (AD-13). `pytest tests/engine/` → 148 passed, 6 skipped, zero LLM calls. Status → done. |

## Review Findings

_From bmad-code-review of the Epic 4 engine (2026-07-10). Covers `safe_to_spend.py` (4-2) and `confidence_score.py` (4-4)._

- [x] [Review][Decision→Patch] Engine evidence strings embed unformatted currency (AD-13) — **RESOLVED (user: format via formatINR).** Driver/explanation prose now routes ₹ through `formatINR` (→ "₹9,500") and the predicted-commitment date through `formatDate` (→ "27 Jun 2026") in `safe_to_spend.py` + `confidence_score.py`. `formatINR`/`formatDate` are framework-agnostic (`services/utils/format.py`) — boundary guard stays green. Two test assertions updated to the grouped form.
- [x] [Review][Patch] `surfaced_predictions` wrongly set for a predicted commitment due AFTER next income [services/engine/safe_to_spend.py:220](../../services/engine/safe_to_spend.py#L220) — **FIXED.** Now gates on `driver is not None` (a prediction lowers confidence only when actually surfaced), so a predicted commitment due after income no longer downgrades `prediction_confidence`. Added regression test `test_predicted_after_income_does_not_lower_confidence`.
- [x] [Review][Defer] After-income layer double-counts current balance [services/engine/safe_to_spend.py:180](../../services/engine/safe_to_spend.py#L180) — deferred; already tracked in contract §8 / story 4-3 (the ₹1,830-vs-~990 scenario-3 open item awaiting spec-owner call).
- [x] [Review][Defer] `safety_ok=True` while STS=₹0 when balance covers commitments but not the buffer [services/engine/safe_to_spend.py:252](../../services/engine/safe_to_spend.py#L252) — deferred; untested boundary (reserved ≤ balance < reserved+buffer → pool<0 → STS 0, score ~40). Mild CS-4 tension; decide whether the buffer belongs in `safety_ok` or document the split.
- [x] [Review][Defer] Overdue predicted commitment (due before `as_of`) is surfaced, not reserved [services/engine/safe_to_spend.py:148](../../services/engine/safe_to_spend.py#L148) — deferred; `days_until_due < 0` falls to the "outside window" branch, so an overdue *critical* prediction goes unreserved (a known overdue is reserved). Defensible (predicted = uncertain, may be paid) but touches "safety beats precision"; revisit with the auto-detect commitments work (Epic 5 / S7.1).
