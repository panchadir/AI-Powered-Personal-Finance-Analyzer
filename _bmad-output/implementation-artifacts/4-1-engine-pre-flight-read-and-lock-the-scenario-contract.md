---
baseline_commit: d0b4a8f5d79cf208e1da96527944e54c0d796e04
---

# Story 4.1: Engine Pre-Flight — Read and Lock the Scenario Contract

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As the **developer building the Financial Engine (Epic 4)**,
I want **to read, reconcile, and lock the Safe-to-Spend / Confidence-Score scenario contract into a single build-ready spec artifact**,
so that **stories 4-2 (engine) and 4-3 (pytest gate) implement and assert against one unambiguous, discrepancy-free contract — never an invented or drifting one under deadline**.

> **This is a pre-flight analysis/spec story (epic S4.0). It writes NO engine code.** Its only deliverable is a locked contract document that 4-2 implements and 4-3 tests. The engine + its tests are the MVP quality gate ("green before the dashboard is wired") and the honesty/safety spine that is *never* cut — so getting the contract exactly right here is what makes 4-2/4-3 flawless. ~2h of work; must be done before 4-2.

## Acceptance Criteria

1. **The locked contract exists.** A new artifact `_bmad-output/implementation-artifacts/4-1-engine-contract.md` is created that is the single source of truth for stories 4-2 and 4-3. It contains: (a) the frozen scenario table (all 13 rows, exact inputs → exact expected outputs), (b) the Reservation Rule (DD-1), (c) the buffer decision (DD-2), (d) the exact evidence-pack output shape, (e) the exact engine input shape, (f) the CS-1..CS-4 Confidence-Score companion assertions.

2. **Scenario count is locked at 13 and the PRD discrepancy is resolved in writing.** [`safe-to-spend-scenarios.md`](../planning-artifacts/safe-to-spend-scenarios.md) enumerates **13** scenarios (7 core + 6 boundary); PRD FR-4 AC still says "12 total". The scenario file + epic story `4-3-...-all-13-scenarios` are authoritative. The contract states: **13 scenarios**, with scenario 13 (payday-is-today, `days=0` ÷0 guard) being the row PRD FR-4's count omits. This reconciliation is recorded as a Decision in the contract artifact.

3. **Every evidence-pack field name is confirmed against the canonical data model.** The contract's field names match `finance_app/models.py` exactly — in particular `score_events` uses `trigger_event` (NOT `triggering_event`) and `suggested_action` (NOT `action`) per AD-9 / CS-3. Any evidence-pack field that maps to a persisted column is annotated with its `models.py` source.

4. **The Reservation Rule (DD-1), criticality windows (FR-4.3), buffer (DD-2), and rounding/floor/÷0 rules (AD-8 + Seam) are transcribed verbatim into the contract** as the behavioral spec 4-2 implements — with the four DD-1 sub-rules, the 7/5/3-day proximity windows, top-of-range variable reserve, and the `days_until_next_confirmed_income ∈ {0, undefined}` guard each stated explicitly.

5. **`safety_ok` truth table is fixed:** `True` for scenarios 1–9, 11, 12, 13; `False`-with-honest-shortfall for scenario 10. Recorded in the contract as an explicit per-scenario column so 4-3 can assert it row-by-row.

6. **Open assumptions are flagged, not silently resolved.** DD-2's "buffer ₹2,000 — documented assumption to confirm during build" is either confirmed (default ₹2,000, per-user configurable, stated in every scenario) or raised as a question — never quietly changed. Same for any scenario input that is under-specified (e.g. scenario 3's "After salary: ~₹990/day" is approximate — the contract states whether 4-3 asserts it exactly or within a tolerance).

## Tasks / Subtasks

- [x] **Task 1 — Read the three source-of-truth documents end to end (AC: 1, 4)**
  - [x] Read [`safe-to-spend-scenarios.md`](../planning-artifacts/safe-to-spend-scenarios.md) fully: the formula, DD-1, DD-2, the evidence-pack output block, all 13 scenario rows, the CS-1..CS-4 companion assertions, and the implementation note.
  - [x] Read PRD [`prd.md`](../planning-artifacts/prd.md) **FR-4** (Safe-to-Spend, incl. FR-4.1..FR-4.12) and **FR-5** (Confidence Score, incl. FR-5.1..FR-5.8).
  - [x] Read `ARCHITECTURE-SPINE.md` **AD-1** (engine/narrate boundary), **AD-8** (STS formula/floor/rounding), **AD-9** (score_events write path), and the `project-context.md` **Seams** entry `[STS denominator guard]`.
- [x] **Task 2 — Reconcile the 12-vs-13 scenario-count discrepancy (AC: 2)**
  - [x] Confirm the scenario file has 13 rows and PRD FR-4 AC says 12; identify scenario 13 (payday-is-today ÷0 guard) as the delta.
  - [x] Record the resolution "lock at 13; scenario file wins over the stale PRD count" as a dated Decision in the contract artifact.
- [x] **Task 3 — Verify evidence-pack + input field names against `finance_app/models.py` (AC: 3)**
  - [x] Cross-check every output field against the canonical `ScoreEvent` model: `trigger_event`, `suggested_action` (NOT `triggering_event` / `action`); and `Commitment` fields `name, amount (Decimal), due_day, criticality`.
  - [x] Confirm criticality enum values are exactly `critical | important | flexible` (default `important`) per `services/utils/enums.py` — note the scenario file uses "medium/low" prose (e.g. scenario 4 "medium", scenario 5 "critical"); map that prose to the real enum in the contract.
- [x] **Task 4 — Author `4-1-engine-contract.md` (AC: 1, 4, 5, 6)**
  - [x] Transcribe the frozen 13-row scenario table with a per-row `safety_ok` column and a `prediction_confidence` column.
  - [x] Write the locked **engine input shape** and **evidence-pack output shape** (as a typed spec — dataclass-style pseudocode, see Dev Notes) that 4-2 will implement and 4-3 will assert on.
  - [x] Transcribe DD-1 (4 sub-rules), FR-4.3 windows (7/5/3), DD-2 buffer, AD-8 rounding/floor, and the ÷0/undefined guard behavior.
  - [x] Transcribe CS-1..CS-4 companion assertions.
  - [x] List open assumptions (buffer default, scenario-3 "~₹990" tolerance, any others found) under a "Decisions & Open Assumptions" heading.
- [x] **Task 5 — Self-check the contract (AC: 5, 6)**
  - [x] Spot-arithmetic 3 scenarios by hand (e.g. #1, #2, #6) to confirm the table's `STS today` equals `floor((pool)/days /10)*10` and the reservations obey DD-1 — catch any typo in the source table before 4-2 trusts it.
  - [x] Confirm the `safety_ok` truth table covers all 13 rows with no gaps.

## Dev Notes

### What "lock the contract" produces (the concrete deliverable)
This story's output is **one markdown file**: `_bmad-output/implementation-artifacts/4-1-engine-contract.md`. It is a *spec*, not code. It exists because the PRD, epics, and roadmap all referenced "the 7 WoZ scenarios" that were never written down until [`safe-to-spend-scenarios.md`](../planning-artifacts/safe-to-spend-scenarios.md) enumerated them — and that file still has a live discrepancy with the PRD count (12 vs 13). Locking it now means 4-2 codes against a frozen target and 4-3 asserts against the same frozen target, so they cannot drift.

### The locked input/output shapes (propose these in the contract; 4-2 implements them)
The engine is **pure, deterministic, framework-agnostic Python** (AD-1, AD-14). Nothing here imports `reflex`/`rx.*`. Propose typed shapes so 4-2 has an unambiguous target — money is `Decimal`, never `float` (AD-8, Agent-Misread Guard):

```python
# services/engine/safe_to_spend.py — PROPOSED contract (finalize in 4-1-engine-contract.md)
from dataclasses import dataclass, field
from decimal import Decimal
from datetime import date

@dataclass(frozen=True)
class CommitmentInput:
    name: str
    amount: Decimal                    # for variable bills, this is the TOP of range
    amount_min: Decimal | None = None  # set only for variable-amount commitments
    due_date: date | None = None
    criticality: str = "important"     # 'critical' | 'important' | 'flexible' (enums.py)
    is_predicted: bool = False         # True = detected-from-history (DD-1 rule 2)

@dataclass(frozen=True)
class EngineInput:
    available_balance: Decimal
    buffer: Decimal = Decimal("2000")  # DD-2 default; per-user configurable
    commitments: tuple[CommitmentInput, ...] = ()
    next_income_date: date | None = None       # None => no confirmed income (÷undefined guard)
    next_income_amount: Decimal | None = None
    income_confidence: str = "High"            # 'Low'|'Medium'|'High'
    as_of: date = ...                          # "today" — drives days_to_income & window math

@dataclass(frozen=True)
class EvidencePack:                    # FR-4.12 — tests assert EVERY field by name
    reserved_total: Decimal
    spendable_pool: Decimal           # = balance - reserved_total - buffer
    days_to_income: int | None        # None when no confirmed income; 0 == payday today
    safe_to_spend_today: Decimal      # max(0, ...), floored down to nearest ₹10
    safe_to_spend_after_income: Decimal | None   # null when no income detected (FR-4.8)
    prediction_confidence: str        # 'Low' | 'Medium' | 'High'
    drivers: tuple[str, ...]          # human-readable reservation drivers
    data_quality_flags: tuple[str, ...]   # e.g. 'no_income_detected'
    safety_ok: bool                   # True iff every commitment due <= next income is covered
```
Field names above are the **exact** FR-4.12 struct. The contract must state whether the engine returns a dataclass or a dict — recommend a frozen dataclass (typed, immutable, test asserts by attribute). Persisted-column field names must match `finance_app/models.py:ScoreEvent` (Story 4-4's concern, but lock the names now): `trigger_event`, `suggested_action`.

### Non-negotiable engine rules to transcribe into the contract (these ARE the spec)
- **AD-8 formula:** `safe_to_spend_today = max(0, (available_balance − reserved_total − buffer) ÷ days_until_next_confirmed_income)`. `max(0, …)` floor is non-negotiable (never negative). Round **down** to nearest ₹10 with `math.floor(x / 10) * 10` — **rounding up is forbidden**. All STS figures end in `0`.
- **DD-1 Reservation Rule** (4 sub-rules): (1) known commitment (confirmed amount+date) due on-or-before next income → **always fully reserved** regardless of window; (2) predicted/uncertain → reserved **only inside** its criticality window (critical 7d / important 5d / flexible 3d), else it lowers Prediction Confidence + is surfaced but NOT subtracted; (3) variable-amount → reserve **top of range**; (4) commitment due **on income day** → reserved against current balance **unless** income confidence High AND income ≥ commitment.
- **DD-2 buffer:** default ₹2,000, per-user configurable; every scenario states it explicitly.
- **[STS denominator guard] (Seam, binding):** `days_until_next_confirmed_income` can be `0` (payday today, scenario 13) or `undefined` (no confirmed income, scenario 12). Guard **before** dividing — never `ZeroDivisionError`, `Infinity`, or `NaN`. Defined fallback: reserved-only mode `safe_to_spend_today = max(0, spendable_pool)` (undivided). Scenario 12 covers `undefined`; scenario 13 covers `0`. Neither may be skipped — this is the payday-morning crash guard.
- **`safety_ok` truth table:** `True` for scenarios **1–9, 11, 12, 13**; `False` (honest shortfall) for **10**.

### The 13 scenarios (source table to freeze — verify each row before trusting it)
Core 1–7 (healthy mid-cycle · critical-in-7d · low-balance-day-before-payday two-layer · variable-bill-top-of-range · predicted-outside-window · collision · cold-start-Low-conf) and boundary 8–13 (due-date-today off-by-one · payday-tomorrow-same-day-commitment ÷1 guard · shortfall-floored-to-₹0 · over-conservatism guard non-zero STS · salary-not-detected null+`no_income_detected` · payday-today ÷0 guard). Exact inputs/outputs live in [`safe-to-spend-scenarios.md`](../planning-artifacts/safe-to-spend-scenarios.md) — **copy them verbatim** into the contract; do not paraphrase the numbers.

### CS-1..CS-4 companion assertions (transcribe verbatim)
- **CS-1** Score = preparedness only; S6 (tight-but-covered) < S1 (comfortable); **S10 (shortfall) scores lowest**; app-usage never moves it.
- **CS-2** Prediction Confidence = data completeness; High in S1/S2/S6, Medium in S4/S5, **Low in S7**; independent of the Score.
- **CS-3** Every score delta writes a `score_events` row `(delta, trigger_event, explanation, suggested_action)`; a change with no matching row **fails the test**. Field names exact: `trigger_event`, `suggested_action`.
- **CS-4** No contradiction: invalid if Score says "well prepared" while STS is ₹0 — S10 must show low Score **and** ₹0 (one story).

### Project Structure Notes
- **Deliverable path:** `_bmad-output/implementation-artifacts/4-1-engine-contract.md` (a planning artifact, not source). This story touches **no** files under `services/` or `finance_app/`.
- `services/engine/` currently holds only `__init__.py` (scaffolded empty by Story 1.1). 4-2 will add `safe_to_spend.py`; 4-4 adds `confidence_score.py`. This story creates neither.
- **Alignment:** the contract must be consistent with `finance_app/models.py` (already merged: `Commitment`, `ScoreEvent`, `Transaction`) and `services/utils/enums.py` (`Criticality = critical|important|flexible`). If the scenario file's prose ("medium"/"low") can't be mapped cleanly to the enum, flag it in Task 3 rather than inventing an enum value.
- **Detected variance to record:** PRD FR-4 AC count (12) vs scenario file / epic 4-3 (13). Resolution: 13 wins (AC 2).

### Testing standards summary
- This story ships **no code**, so it has **no pytest**. Its "test" is the Task 5 self-check: hand-verify 3 scenarios' arithmetic and confirm the `safety_ok` table has all 13 rows.
- It sets up the real gate: `pytest services/engine/` (story 4-3) must be **green with zero LLM calls** (AD-1), enforced by a fixture that injects an LLM client which **raises on construction/use**. Note this requirement in the contract so 4-2/4-3 build it in.

### References
- [Source: _bmad-output/planning-artifacts/safe-to-spend-scenarios.md] — the 13-scenario table, DD-1, DD-2, evidence-pack block, CS-1..CS-4 (the primary contract).
- [Source: _bmad-output/planning-artifacts/prd.md#FR-4] — Safe-to-Spend FR-4.1..FR-4.12 (formula, reservation rule, criticality tiers, buffer, two-layer, undetected-salary, shortfall, output struct).
- [Source: _bmad-output/planning-artifacts/prd.md#FR-5] — Confidence Score FR-5.1..FR-5.8 (preparedness-only, prediction confidence, event binding, cold start, over-conservatism guard FR-5.8).
- [Source: _bmad-output/planning-artifacts/epics-and-stories.md#E4] — E4 goal + stories S4.0..S4.4; cut-order ("never cut S4.1–S4.4").
- [Source: _bmad-output/planning-artifacts/architecture/.../ARCHITECTURE-SPINE.md#AD-8] — STS formula, floor, ₹10 round-down.
- [Source: ARCHITECTURE-SPINE.md#AD-1] — engine/narrate hard boundary; engine tests run with zero LLM calls.
- [Source: ARCHITECTURE-SPINE.md#AD-9] — score_events as the score write path; `trigger_event` spelling.
- [Source: _bmad-output/project-context.md#Seams] — `[STS denominator guard]` ÷0/undefined behavior (binding).
- [Source: finance_app/models.py] — canonical `Commitment`, `ScoreEvent` (field names `trigger_event`, `suggested_action`), `Transaction`.
- [Source: services/utils/enums.py] — `Criticality` enum values.

## Dev Agent Record

### Agent Model Used

claude-opus-4-8 (Claude Code / BMAD dev-story)

### Debug Log References

- Self-check arithmetic (Task 5), hand-verified against `math.floor(pool/days/10)*10`:
  - S1: 42000−15000−2000=25000 → ⌊25000/20/10⌋×10 = **1250** ✓
  - S2: 22000−15000−2000=5000 → ⌊5000/6/10⌋×10 = **830** ✓ (6×830=4980 ≤ 5000)
  - S6: 30000−24300−2000=3700 → ⌊3700/5/10⌋×10 = **740** ✓ (5×740=3700)
  - S4: top-of-range 3000 → reserved 18000, pool 8000 → **570** ✓ (midpoint 2250 would wrongly give 625)
- No code shipped ⇒ no `pytest` run for this story (per Dev Notes: the "test" is the Task 5 self-check). The real `pytest services/engine/` gate is set up by story 4-3.

### Completion Notes List

- **Deliverable:** `_bmad-output/implementation-artifacts/4-1-engine-contract.md` — the LOCKED engine contract (single source of truth for 4-2 and 4-3).
- **Key decisions locked** (see contract §8):
  1. Scenario count **13**, not 12 — scenario file + epic 4-3 win over the stale PRD FR-4 AC count; the delta is scenario 13 (payday-today ÷0 guard). Recommend a later one-line PRD docs fix (non-blocking).
  2. Criticality prose→enum mapping: **medium→`important` (5d)**, **low→`flexible` (3d)**; `critical`→7d. 4-2 uses the enum only.
  3. Engine returns a **frozen `EvidencePack` dataclass** (typed, immutable), not a dict.
  4. Buffer default **₹2,000** confirmed (DD-2), passed as an `EngineInput` param for per-user override; persistence out of scope for Epic 4.
  5. Field-name lock for 4-4: `score_events` → `trigger_event` / `suggested_action` (AD-9/CS-3), referenced via model attribute.
- **Open item carried forward:** scenario 3's "~₹990/day" after-income figure is approximate in the source — contract instructs 4-3 to assert the *today* layer exactly (₹150) and the *after-income* layer within ±₹10 until 4-2 pins the exact computed value.
- **Requirement carried to 4-3:** `pytest services/engine/` must run with zero LLM calls, enforced by a raising-client fixture (AD-1).
- **Scope hygiene:** analysis/spec story only — touched **no** files under `services/` or `finance_app/`.

### File List

- `_bmad-output/implementation-artifacts/4-1-engine-contract.md` (new — the deliverable)
- `_bmad-output/implementation-artifacts/4-1-engine-pre-flight-read-and-lock-the-scenario-contract.md` (this story file: frontmatter `baseline_commit`, task checkboxes, Dev Agent Record, Change Log, Status)
- `_bmad-output/implementation-artifacts/sprint-status.yaml` (epic-4 → in-progress; 4-1 → in-progress → review; last_updated → 2026-07-10)

## Change Log

| Date | Change |
|---|---|
| 2026-07-10 | Story created (ready-for-dev) via bmad-create-story. |
| 2026-07-10 | Implemented: authored locked `4-1-engine-contract.md`; reconciled 12→13 scenario-count discrepancy; locked criticality enum mapping, evidence-pack/input shapes, buffer default, and CS-1..CS-4. Self-check passed. Status → review. |
