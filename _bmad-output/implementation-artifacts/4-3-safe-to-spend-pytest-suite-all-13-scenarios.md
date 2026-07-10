---
baseline_commit: d0b4a8f5d79cf208e1da96527944e54c0d796e04
---

# Story 4.3: Safe-to-Spend pytest Suite — All 13 Scenarios (the MVP Quality Gate)

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As the **team shipping the finance analyzer**,
I want **a table-driven pytest suite that asserts every field of the engine's evidence pack across all 13 locked scenarios and proves the two indicators never contradict**,
so that **the deterministic engine is provably correct and safe before the dashboard is wired to it — this suite is the Day-2 go/no-go and the product's honesty gate**.

> Implements epic **S4.2** against the LOCKED contract [`4-1-engine-contract.md`](4-1-engine-contract.md) §5–§6, driving the engine built in Story 4-2 (`services/engine/safe_to_spend.py`). **`pytest services/engine/` must be green with ZERO LLM calls (AD-1)** — enforced by the `_forbid_anthropic` fixture from 4-2. This is part of the honesty/safety spine that is **never cut**.

## Acceptance Criteria

1. **Table-driven suite over all 13 scenarios.** A `@pytest.mark.parametrize` suite in `tests/engine/test_scenarios.py` covers scenarios **1–13** from contract §5 (7 core + 6 boundary), each a named case (`id=`), asserting the evidence-pack fields the contract locks for that row: `reserved_total`, `spendable_pool`, `days_to_income`, `safe_to_spend_today`, and `safety_ok`.

2. **`safety_ok` truth table holds exactly (contract §5):** `True` for scenarios **1–9, 11, 12, 13**; `False` for **10** (with the honest-shortfall driver naming the ₹9,500 gap). Asserted per row.

3. **Rounding + floor invariants asserted globally:** every `safe_to_spend_today` across all 13 scenarios is `>= 0` and ends in `0` (`% 10 == 0`); scenario 10 returns exactly `₹0` (not negative, no crash).

4. **Two-layer / salary / ÷0 boundaries asserted:** scenario 12 → `safe_to_spend_after_income is None` **and** `"no_income_detected" in data_quality_flags`; scenario 13 → `days_to_income == 0` and no exception (reserved-only fallback); scenario 3 → `safe_to_spend_today == ₹150` **exactly** (today layer is locked).

5. **CS-2 (Prediction Confidence) asserted per scenario (contract §6):** `prediction_confidence` is **High** in S1/S2/S6, **Medium** in S4/S5, **Low** in S7. To make S7 → `Low`, the engine gains a minimal, documented data-completeness signal (see Dev Notes); this is the only permitted engine change in this story.

6. **CS-4 (no contradiction) asserted:** for scenario 10, `safe_to_spend_today == 0` **and** `safety_ok is False` — the two indicators tell one story (never "well-prepared" while STS is ₹0). *(CS-1 score-ordering and CS-3 `score_events` binding require the 0–100 Confidence Score + writeback from Story 4-4 and are asserted there — documented boundary, not a gap.)*

7. **Scenario-3 after-income reconciliation recorded (contract §8 open item):** the suite asserts scenario 3's **today** layer exactly (₹150) and the after-income layer **structurally** (`is not None`, `> 0`, `% 10 == 0`) — NOT against the scenario file's flagged-approximate "~990", which does not reconcile from the stated inputs. A `Decision` note in this story records the resolution and the exact engine value (₹1,830) for a future scenario-file/spec fix.

8. **Green gate, zero LLM calls.** `pytest tests/engine/` passes in full (4-2's targeted tests + this 13-scenario suite), with the `_forbid_anthropic` autouse fixture active. `tests/test_service_boundary.py` stays green.

## Tasks / Subtasks

- [x] **Task 1 — Build the 13-scenario input fixtures (AC: 1)**
  - [x] In `tests/engine/test_scenarios.py`, encoded each of the 13 scenarios from contract §5 / [`safe-to-spend-scenarios.md`](../planning-artifacts/safe-to-spend-scenarios.md) as an `EngineInput` with exact inputs. `as_of`/dates chosen so `days_to_income` matches the contract's `days` column exactly.
  - [x] Mapped scenario-file prose criticality to the enum: "critical"→`critical`, "medium"→`important`, "low"→`flexible` (contract §2a).
- [x] **Task 2 — Parametrized evidence-pack assertions (AC: 1, 2, 3)**
  - [x] One parametrized `Case` per scenario (`id="s1_healthy_mid_cycle"`, … `id="s13_payday_today"`), asserting `reserved_total`, `spendable_pool`, `days_to_income`, `safe_to_spend_today`, `safety_ok` against the contract §5 table.
  - [x] Global invariant asserts: `safe_to_spend_today >= 0` and `% 10 == 0` for all 13; S10 STS `== 0`.
- [x] **Task 3 — Boundary + two-layer assertions (AC: 4, 7)**
  - [x] S12: `safe_to_spend_after_income is None` + `"no_income_detected"` flag. S13: `days_to_income == 0`, no exception. S3: today `== ₹150` exact; after-income structural (`is not None`, `> 0`, `% 10 == 0`).
- [x] **Task 4 — Prediction Confidence + minimal data-completeness signal (AC: 5) — RED then GREEN**
  - [x] Assertions: Pred.Conf High in S1/S2/S6, Medium in S4/S5, Low in S7 (skipped where contract §5 leaves it unpinned, S8–S13).
  - [x] Extended `EngineInput` with a minimal, documented `low_data: bool = False` signal; `_prediction_confidence` returns `"Low"` when set (cold-start, S7). Existing High/Medium logic preserved; module docstring updated. Only engine change in this story.
- [x] **Task 5 — CS-4 no-contradiction assertion (AC: 6)**
  - [x] Asserted S10: `safe_to_spend_today == 0` AND `safety_ok is False`. Comment points to Story 4-4 for CS-1 (score ordering) and CS-3 (`score_events` binding).
- [x] **Task 6 — Green gate (AC: 8)**
  - [x] `pytest tests/engine/ tests/test_service_boundary.py` → **111 passed, 6 skipped**, zero LLM calls. No test constructs an Anthropic client (autouse guard active).
  - [x] Recorded the scenario-3 after-income Decision (AC 7) in Completion Notes.

## Dev Notes

### THE contract to assert against
[`4-1-engine-contract.md`](4-1-engine-contract.md) §5 (the frozen 13-row table with per-row `safety_ok`), §6 (CS-1..CS-4), §7 (hand-verified arithmetic), §8 (decisions incl. the scenario-3 after-income open item). Full scenario inputs: [`safe-to-spend-scenarios.md`](../planning-artifacts/safe-to-spend-scenarios.md). **Where this story and the contract disagree, the contract wins — raise it, don't silently resolve.**

### The 13 expected rows (contract §5 — assert these; do not paraphrase the numbers)
| # | reserved | pool | days | STS today | pred.conf | safety_ok |
|---|---|---|---|---|---|---|
| 1 | 15000 | 25000 | 20 | 1250 | High | True |
| 2 | 15000 | 5000 | 6 | 830 | High | True |
| 3 | 0 (today layer) | 150 | 1 | 150 | High | True |
| 4 | 18000 | 8000 | 14 | 570 | Medium | True |
| 5 | 15000 | 13000 | 17 | 760 | Medium | True |
| 6 | 24300 | 3700 | 5 | 740 | High | True |
| 7 | 15000 | 8000 | 10 | 800 | **Low** | True |
| 8 | 8500 | 29500 | 27 | 1090 | — | True |
| 9 | 15000 | 1000 | 1 | 1000 | — | True |
| 10 | 23500 | −9500 | any | **0** | — | **False** |
| 11 | 0 | 28000 | 20 | 1400 | — | True |
| 12 | 0 | 18000 | None | 18000* | — | True |
| 13 | 0 | 18000 | 0 | 18000 | — | True |

\* S12 `safe_to_spend_today` = reserved-only fallback `max(0, pool)` = 18000; the UI shows the FR-4.8 "add a salary" prompt (driven by the `no_income_detected` flag), not this number. Assert the flag + `after_income is None`; asserting the exact 18000 is optional but consistent with contract §1a.

### Encoding the trickier scenarios (translate carefully)
- **S3 (day before payday):** `available_balance=2150, buffer=2000`, no commitments, `next_income_date = as_of + 1 day`, `next_income_amount=55000`, `income_confidence=High`. today=150. **After-income:** engine returns 1830 (contract §8 open item) — assert structurally, not "~990".
- **S4 (variable, top-of-range):** electricity `CommitmentInput(amount=3000, amount_min=1500, criticality="important", is_predicted=True or known)` due within its 5d window; rent 15000 known. reserved 18000, pred.conf Medium.
- **S5 (predicted outside window):** detected EMI `amount≈5000, criticality="critical", is_predicted=True`, `due_date = as_of + 12 days` (outside 7d) → not reserved; reserved stays 15000 (rent), pred.conf Medium, surfaced driver present.
- **S6 (collision):** rent 15000 + EMI 8500 + broadband 800 all known, all due before income → reserved 24300.
- **S7 (cold start):** set the new `low_data` signal → pred.conf Low; rent 15000 reserved (critical, reserved despite low confidence).
- **S8 (due today):** EMI 8500 `due_date == as_of` (critical) → reserved; `days_to_income = 27`.
- **S9 (payday tomorrow, same-day rent, income Medium):** rent 15000 `due_date == next_income_date`, `income_confidence="Medium"` → reserved from present balance (DD-1 rule 4); days=1; STS 1000.
- **S11 (over-conservatism guard):** no commitments, days=20 → STS 1400 (must be > 0).

### The one permitted engine change (AC 5) — data-completeness signal for S7 `Low`
The evidence pack must carry `prediction_confidence`, and S7 requires `Low`. The 4-2 engine only derives High/Medium (variable-bill / surfaced-prediction). Add a **minimal** field to `EngineInput` (recommend `low_data: bool = False`, or `history_days: int | None = None` with `Low` when history is thin) and return `"Low"` when set. Keep it small and documented — the fuller preparedness model + the 0–100 Confidence Score live in Story 4-4. Do **not** expand engine behavior beyond this in this story.

### Scope boundary (what belongs to 4-4, not here)
- **CS-1** (Confidence Score 0–100 ordering: S6 < S1, S10 lowest) and **CS-3** (`score_events` row per delta) require `services/engine/confidence_score.py` + the `score_events` writeback — **Story 4-4**. This suite asserts **CS-2** (prediction confidence) and **CS-4** (no contradiction, via STS/`safety_ok`) only, and leaves a comment marking where 4-4 extends the suite. Do not build `confidence_score.py` here.

### Testing standards summary
- New file `tests/engine/test_scenarios.py`; reuses `tests/engine/conftest.py` (the `_forbid_anthropic` autouse guard — do not duplicate it). Import `from services.engine.safe_to_spend import ...`.
- Prefer a `@dataclass`/`namedtuple` `Case(name, engine_input, expected_...)` list parametrized with `ids=[c.name for c in CASES]` for readable failures.
- Assert `Decimal` equality with `Decimal` literals (never float). Money ends in `0`.
- `pytest tests/engine/` green with zero LLM calls is the gate (AD-1). Keep 4-2's targeted tests passing too.

### Project Structure Notes
- **New:** `tests/engine/test_scenarios.py`. **Edited (minimal):** `services/engine/safe_to_spend.py` (add the `low_data`/`history_days` signal for S7 `Low`; update docstring), and its `EngineInput` — a backward-compatible new field with a default, so 4-2's tests keep passing.
- **Does not touch** `finance_app/` or Reflex. Does not create `confidence_score.py` (4-4).
- **Detected variance (recorded):** scenario-3 after-income "~990" (scenario file) ≠ engine's 1830 (from the stated inputs). Resolution per contract §8: assert today exactly, after-income structurally; flag for a scenario-file/spec fix. Do not hardcode 990.

### Previous story intelligence (4-2)
- 4-2 built the engine + a zero-LLM `conftest.py` (reuse it) + representative tests for S1/S2/S10/S12/S13 — those already pass; this story adds the **remaining** scenarios (3,4,5,6,7,8,9,11) and the prediction-confidence/CS-2 + CS-4 assertions.
- 4-2 flagged: S3 after-income = 1830 (not ~990); `prediction_confidence` Low needs a data-completeness signal (this story adds it); `safety_ok = available_balance >= reserved_total`.
- 4-2 verified S1→1250, S2→830, S6-style math (740), S4 top-of-range (570 not 625) by hand — reuse those expected values.

### References
- [Source: _bmad-output/implementation-artifacts/4-1-engine-contract.md] §5 (13-row table), §6 (CS-1..CS-4), §7 (arithmetic), §8 (decisions). Primary.
- [Source: _bmad-output/implementation-artifacts/4-2-safe-to-spend-engine-implementation.md] — engine API, `safety_ok` definition, scenario-3 flag.
- [Source: _bmad-output/planning-artifacts/safe-to-spend-scenarios.md] — full inputs for all 13 rows + CS-1..CS-4 companion assertions + implementation note ("go/no-go for Day 2").
- [Source: _bmad-output/planning-artifacts/prd.md#FR-4] AC — 12→13 reconciliation; per-field assertion requirement. [#FR-5.8] over-conservatism guard (S11). [#FR-4.8] undetected salary (S12).
- [Source: ARCHITECTURE-SPINE.md#AD-1] — engine tests run with zero LLM calls (the raising-client fixture).
- [Source: services/engine/safe_to_spend.py] — the engine under test; [tests/engine/conftest.py] — the zero-LLM guard to reuse.

## Dev Agent Record

### Agent Model Used

claude-opus-4-8 (Claude Code / BMAD dev-story)

### Debug Log References

- `pytest tests/engine/ tests/test_service_boundary.py -q` → **111 passed, 6 skipped in 0.24s**, zero LLM calls. The 6 skips are `test_prediction_confidence_where_locked` for S8–S13 (contract §5 leaves prediction confidence unpinned for the boundary rows — skipped, not failed).
- All 13 scenarios pass every locked field: `reserved_total`, `spendable_pool`, `days_to_income`, `safe_to_spend_today`, `safety_ok`, plus prediction confidence for S1–S7. Story 4-2's targeted tests still pass (no regression from the `low_data` change).

### Completion Notes List

- **New file `tests/engine/test_scenarios.py`** — table-driven `Case` dataclass list parametrized with readable `ids` (`s1_healthy_mid_cycle` … `s13_payday_today`). Reuses 4-2's `conftest.py` zero-LLM guard (not duplicated).
- **All 13 contract §5 rows green**, exact `Decimal` assertions; dates chosen so `days_to_income` matches the `days` column. safety_ok truth table verified: True for 1–9, 11, 12, 13; False for 10 only.
- **Engine change (the single permitted one):** added `EngineInput.low_data: bool = False`; `_prediction_confidence` returns `"Low"` when set → S7 cold-start Low (FR-5.4). Backward-compatible default; 4-2 tests unaffected.
- **DECISION — scenario-3 after-income (contract §8 open item, resolved for the gate):** asserted the **today layer exactly (₹150)** and the **after-income layer structurally** (`is not None`, `> 0`, `% 10 == 0`). The engine returns **₹1,830** from scenario 3's stated inputs; the scenario file's "~₹990/day" is a flagged approximation that assumes next-cycle commitments not present in the stated inputs, so it is **not** asserted verbatim. **Follow-up for the spec owner:** either add the next-cycle commitments to scenario 3 in `safe-to-spend-scenarios.md` (to justify ~990) or update the file's figure to the engine's ₹1,830. Recorded, not silently resolved.
- **CS scope honored:** this suite asserts **CS-2** (prediction confidence per scenario) and **CS-4** (no contradiction: S10 shows STS ₹0 + `safety_ok=False`). **CS-1** (0–100 score ordering) and **CS-3** (`score_events` binding) require `confidence_score.py` + the writeback and are **Story 4-4** — marked with a comment in the suite. Did not build `confidence_score.py` here.
- **Gate status:** `pytest services/engine/` (via `tests/engine/`) is **green with zero LLM calls** — the Day-2 go/no-go the contract and PRD FR-4 AC require, satisfied before any dashboard wiring.

### File List

- `tests/engine/test_scenarios.py` (new — the 13-scenario parametrized gate + CS-2/CS-4)
- `services/engine/safe_to_spend.py` (edited — added `low_data` field + `Low` derivation; docstring/notes)
- `_bmad-output/implementation-artifacts/4-3-safe-to-spend-pytest-suite-all-13-scenarios.md` (this story: frontmatter, checkboxes, Dev Agent Record, Change Log, Status)
- `_bmad-output/implementation-artifacts/sprint-status.yaml` (4-3 → in-progress → review; last_updated 2026-07-10)

## Change Log

| Date | Change |
|---|---|
| 2026-07-10 | Story created (ready-for-dev) via bmad-create-story. |
| 2026-07-10 | Implemented the 13-scenario table-driven gate (`tests/engine/test_scenarios.py`) + CS-2/CS-4 assertions; added `low_data` signal to the engine for S7 Low. `pytest tests/engine/` → 111 passed, 6 skipped, zero LLM calls. Recorded scenario-3 after-income decision. Status → review. |
