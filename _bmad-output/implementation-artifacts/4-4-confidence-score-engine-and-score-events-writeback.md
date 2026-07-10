---
baseline_commit: d0b4a8f5d79cf208e1da96527944e54c0d796e04
---

# Story 4.4: Confidence Score Engine & Score-Events Binding

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **user of the finance analyzer**,
I want **a 0–100 preparedness score that only ever reflects how ready my money is (never how much I use the app), always comes with a plain-language reason and a suggested action, and never contradicts my Safe-to-Spend**,
so that **I can trust a single honest signal of my financial preparedness that grows with data instead of a made-up neutral number**.

> Implements epic **S4.3 + S4.4** against the LOCKED contract [`4-1-engine-contract.md`](4-1-engine-contract.md) §6 (CS-1..CS-4). **Deterministic, LLM-free (AD-1); the score is derived from the Safe-to-Spend evidence pack.** Per the 2026-07-10 product decision, the **DB `score_events` writeback is deferred to Epic 5's dashboard handler** — this story delivers the pure engine that *produces* the atomic event fields `(delta, trigger_event, explanation, suggested_action)` so the handler can persist them without any business logic (AD-9). `services/` must not import `finance_app`'s `ScoreEvent` model (AD-2).

## Acceptance Criteria

1. **`services/engine/confidence_score.py` exists** exposing `ScoreResult` (frozen dataclass) and a pure `compute_confidence_score(evidence: EvidencePack, *, previous_score: int | None = None, trigger_event: str = "recalculation") -> ScoreResult`. Re-exported from `services/engine/__init__.py`. No `reflex`/`finance_app` import (AD-1/AD-2).

2. **Score is 0–100 and preparedness-only (FR-5.1):** derived solely from the evidence pack (commitment coverage, buffer health, spendable headroom). No engagement/usage input exists in the signature — structurally impossible to include (CS-1).

3. **CS-1 ordering holds:** `score(S6) < score(S1)` (tight-but-covered scores below comfortable) and **`score(S10)` is the lowest** of {S1, S6, S10} (shortfall lowest). Asserted against evidence packs produced by `compute_safe_to_spend` on those scenarios.

4. **CS-3 event binding (AD-9):** every `ScoreResult` carries non-empty `trigger_event`, `explanation`, and a `suggested_action`, plus a `delta = score − (previous_score or 0)`. An unexplained score change is structurally impossible (the fields are non-optional on the result). Field names match `finance_app/models.py:ScoreEvent` exactly — `trigger_event`, `suggested_action` (NOT `triggering_event` / `action`).

5. **CS-4 no contradiction:** when `evidence.safety_ok is False` (shortfall, S10) the score is in the lowest band **and** the result's explanation is honest about the gap — never a "well-prepared" score while Safe-to-Spend is ₹0.

6. **Cold start (FR-5.4):** the score is **computed immediately** from whatever data exists (no fake neutral-50 default); `prediction_confidence` is passed through from the evidence pack **separately** and is **never conflated** with the 0–100 score (FR-5.2). For S7 (`low_data`) the score is a real computed value and `prediction_confidence == "Low"`.

7. **Tests green, zero LLM calls (AD-1):** `pytest tests/engine/` stays fully green (4-2 + 4-3 + this story), with the `_forbid_anthropic` autouse guard active. New tests cover CS-1 ordering, CS-3 binding (fields + delta), CS-4 no-contradiction, score bounds [0,100], and cold-start.

8. **Writeback contract documented (not built):** the module docstring states the `score_events` insert is performed by the caller (Epic 5 dashboard handler) using the returned `ScoreResult` fields, atomically (AD-9), because `services/` may not import the `rx.Model`. No DB code in this story.

## Tasks / Subtasks

- [x] **Task 1 — `ScoreResult` + module skeleton (AC: 1, 4, 8)**
  - [x] Defined `ScoreResult` (`@dataclass(frozen=True)`): `score`, `delta`, `trigger_event`, `explanation`, `suggested_action`, `prediction_confidence`. Field names mirror `ScoreEvent` for the deferred writeback.
  - [x] Module docstring: preparedness-only, LLM-free, prediction-confidence-separate, and the deferred-writeback contract (AC 8).
  - [x] Imports `EvidencePack` from `services.engine.safe_to_spend` (intra-engine — allowed).
- [x] **Task 2 — Preparedness score (AC: 2, 3, 5) — RED then GREEN**
  - [x] Tests: `score(S1) > score(S6) > score(S10)`; `score` ∈ [0,100] (parametrized over all 13); S10 in lowest band (≤20).
  - [x] Implemented `_preparedness_score(evidence)`: shortfall band `[0,20]` (deeper gap → lower); covered band `[40,95]` scaled by headroom `spendable_pool / (spendable_pool + reserved_total)`. All ratios `Decimal`, clamped. No balance/buffer needed beyond the evidence pack.
- [x] **Task 3 — Explanation + suggested action (AC: 4, 5, 6) — RED then GREEN**
  - [x] Implemented `_explain(evidence) -> (explanation, suggested_action)`: shortfall → names the ₹gap + fix; `no_income_detected` → covered-from-balance + "add your salary"; healthy → breathing-room + "keep your buffer intact". Non-empty always.
  - [x] Tests: explanation/suggested_action non-empty across all 13 scenarios; shortfall explanation contains "exceed".
- [x] **Task 4 — Assemble `compute_confidence_score` + delta binding (AC: 4, 6)**
  - [x] Wired score + explanation + `delta = score − (previous_score or 0)` + pass-through `prediction_confidence`.
  - [x] Tests: delta == score for `previous_score=None`; delta == score−50 for previous 50; `prediction_confidence` equals the evidence pack's (S4 Medium); cold-start S7 → real score (59) + `"Low"`, `!= 50`.
- [x] **Task 5 — Re-export + green gate (AC: 1, 7)**
  - [x] Re-exported `ScoreResult`, `compute_confidence_score` from `services/engine/__init__.py`.
  - [x] `pytest tests/engine/ tests/test_service_boundary.py` → **147 passed, 6 skipped**, zero LLM calls.

## Dev Notes

### Design (build against the evidence pack, not raw balances)
`compute_confidence_score` takes the **`EvidencePack`** from `compute_safe_to_spend` (Story 4-2) — this guarantees the score can never contradict Safe-to-Spend (CS-4) because both read the same computed figures. The evidence pack does **not** carry `available_balance`/`buffer`; use `net = spendable_pool + reserved_total` (= balance − buffer) for the headroom denominator. No need to re-plumb balances.

```python
# services/engine/confidence_score.py
from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from services.engine.safe_to_spend import EvidencePack

@dataclass(frozen=True)
class ScoreResult:
    score: int                    # 0..100 preparedness
    delta: int                    # score - (previous_score or 0)
    trigger_event: str            # -> score_events.trigger_event (exact name, AD-9/CS-3)
    explanation: str              # -> score_events.explanation (plain language, FR-5.6)
    suggested_action: str         # -> score_events.suggested_action (exact name)
    prediction_confidence: str    # pass-through from evidence (Low|Medium|High), NOT the score

def compute_confidence_score(
    evidence: EvidencePack, *, previous_score: int | None = None, trigger_event: str = "recalculation"
) -> ScoreResult:
    ...
```

### Scoring model (deterministic, monotonic, documented)
- **Shortfall (`not safety_ok`) → band [0, 20]:** `severity = min(1, gap / reserved_total)` where `gap = -spendable_pool`; `score = round(20 * (1 - severity))`, floored at 0. Guarantees S10 sits below every covered scenario.
- **Covered (`safety_ok`) → band ~[40, 95]:** `headroom = clamp(spendable_pool / (spendable_pool + reserved_total), 0, 1)`; `score = round(40 + 55 * headroom)`. Comfortable (high headroom) → high; tight-but-covered (low headroom) → ~mid-40s.
- All ratios in `Decimal` (`ROUND_HALF_UP` to int); the **score is an int, not money** — but keep intermediates `Decimal` to honor the engine's no-float ethos. Clamp final to [0,100].
- **Reference values** (from the 4-3 evidence packs, for the CS-1 test — assert the *ordering*, not exact ints, so the model can be tuned): S11≈95 > S1≈74 > S7≈59 > S6≈47 > S10≈12. The locked assertions are `S1 > S6` and `S10` lowest.
- **Factors deferred:** FR-5.1 also names spending-pace and savings-trend — these need transaction history not present in the evidence pack. MVP score uses coverage + buffer + headroom; note the deferral in the docstring.

### Prediction Confidence is separate (FR-5.2 — do NOT conflate)
`prediction_confidence` already lives on the evidence pack (High/Medium/Low, set by `safe_to_spend`). Pass it through on `ScoreResult` for convenience, but it is **not** an input to the 0–100 score and must never be blended into it. The two are shown side by side (score = preparedness; prediction confidence = data completeness).

### Deferred writeback (AC 8 — the product decision of record, 2026-07-10)
`services/` cannot import `finance_app/models.py:ScoreEvent` (AD-2; enforced by `tests/test_service_boundary.py`). So the atomic `score_events` insert is done by the **caller** — the Epic 5 dashboard `rx.State` handler — using the `ScoreResult` fields: it opens a session, writes one `ScoreEvent(score=..., delta=..., trigger_event=..., explanation=..., suggested_action=...)` row, and the UI score is read back from the latest row (AD-9). This story makes that atomic write *possible and honest* by always emitting the four bound fields; it does not perform the write. Document this in the module docstring so Epic 5 wires it correctly.

### Testing standards summary
- New file `tests/engine/test_confidence_score.py`; reuse `tests/engine/conftest.py` (zero-LLM guard — do not duplicate). Build evidence packs by calling `compute_safe_to_spend` on the S1/S6/S7/S10/S12 inputs (reuse the encodings from `tests/engine/test_scenarios.py` — consider importing `CASES` or a couple of `EngineInput`s).
- Assert **orderings** for CS-1 (robust to model tuning), exact **field presence + delta** for CS-3, and bounds. `Decimal` for any money in assertions; the score is an `int`.
- `pytest tests/engine/` green with zero LLM calls is the gate (AD-1).

### Project Structure Notes
- **New:** `services/engine/confidence_score.py`, `tests/engine/test_confidence_score.py`. **Edited:** `services/engine/__init__.py` (add `ScoreResult`, `compute_confidence_score` to re-exports/`__all__`).
- **Does NOT** create/modify `score_events` DB code, `finance_app/`, or any Reflex/`rx.State` code. The writeback is Epic 5.
- `commitments.py` (auto-detection) is **not** part of this story (Epic 5 / S7.1).

### Previous story intelligence (4-2, 4-3)
- The engine + evidence pack (`EvidencePack`) and the zero-LLM `conftest.py` already exist; reuse both. `prediction_confidence` is on the evidence pack (High/Medium/Low; Low via `EngineInput.low_data`).
- `safety_ok = available_balance >= reserved_total`; shortfall (S10) → `safety_ok False`, `spendable_pool` negative, STS `0` — the exact signal CS-4 keys on.
- Scenario evidence packs available from `tests/engine/test_scenarios.py::CASES` — reuse to avoid re-deriving inputs.

### References
- [Source: _bmad-output/implementation-artifacts/4-1-engine-contract.md] §6 (CS-1..CS-4), §4 (evidence-pack shape). Primary.
- [Source: _bmad-output/planning-artifacts/prd.md#FR-5] — FR-5.1 preparedness-only, FR-5.2 prediction confidence separate, FR-5.3 event binding, FR-5.4 cold start (no fake-50), FR-5.6 "why" explanation.
- [Source: ARCHITECTURE-SPINE.md#AD-9] — score_events as the write path; `trigger_event` spelling; UI score = latest event row. [#AD-1] engine LLM-free. [#AD-2] services ↛ finance_app.
- [Source: finance_app/models.py] — `ScoreEvent(score, delta, trigger_event, explanation, suggested_action, timestamp)` — the field names the writeback must match.
- [Source: services/engine/safe_to_spend.py] — `EvidencePack` (the input); [tests/engine/test_scenarios.py] — scenario encodings to reuse; [tests/engine/conftest.py] — zero-LLM guard.

## Dev Agent Record

### Agent Model Used

claude-opus-4-8 (Claude Code / BMAD dev-story)

### Debug Log References

- `pytest tests/engine/ tests/test_service_boundary.py -q` → **147 passed, 6 skipped in 0.27s**, zero LLM calls. New: `tests/engine/test_confidence_score.py`. No regression to 4-2/4-3.
- Computed scores (CS-1 ordering verified): **S11=95 (High) > S1=74 (High) > S7=59 (Low) > S6=47 (High) > S10=12 (High)**. Shortfall (S10) strictly lowest; cold-start (S7) a real 59, not a fake 50.

### Completion Notes List

- **New module `services/engine/confidence_score.py`** — pure `Decimal`, stdlib + intra-engine import only (`EvidencePack`). Public API (`ScoreResult`, `compute_confidence_score`) re-exported from `services/engine/__init__.py`. Boundary test confirms no `reflex`/`finance_app` import.
- **Preparedness-only by construction (CS-1):** the signature accepts *only* an `EvidencePack` — there is no engagement input to accidentally include. Score bands: shortfall `[0,20]`, covered `[40,95]` by headroom `pool/(pool+reserved)`.
- **CS-3 event binding (AD-9):** `ScoreResult` always carries non-empty `trigger_event`/`explanation`/`suggested_action` + a computed `delta` — an unexplained change is structurally impossible. Field names match `ScoreEvent` exactly (`trigger_event`, `suggested_action`).
- **CS-4 no contradiction:** S10 → score 12 (lowest band) with an explanation naming the ₹9,500 gap, while STS is ₹0 — one honest story.
- **CS-2 / cold start (FR-5.2/5.4):** `prediction_confidence` is passed through from the evidence pack and **never** blended into the 0–100 score; S7 cold-start computes a real 59 with `prediction_confidence="Low"` — no fake neutral-50.
- **DEFERRED (product decision 2026-07-10) — `score_events` DB writeback.** `services/` cannot import `finance_app`'s `ScoreEvent` `rx.Model` (AD-2). The atomic insert is done by the **Epic 5 dashboard `rx.State` handler** using the `ScoreResult` fields (documented in the module docstring). This story delivers the pure engine that *produces* the bound fields; it writes no DB row. **Carried to Epic 5:** wire `ScoreEvent(score, delta, trigger_event, explanation, suggested_action)` insert + read-back-latest (AD-9), and add the integration test that asserts the row is written on every score change (the DB half of CS-3).
- **Deferred factors (documented):** FR-5.1's spending-pace / savings-trend need transaction history absent from the evidence pack — MVP score uses coverage + buffer + headroom; noted in the docstring as a future refinement.

### File List

- `services/engine/confidence_score.py` (new — the Confidence Score engine)
- `services/engine/__init__.py` (edited — re-export `ScoreResult`, `compute_confidence_score`)
- `tests/engine/test_confidence_score.py` (new — CS-1/CS-3/CS-4 + bounds + cold-start)
- `_bmad-output/implementation-artifacts/4-4-confidence-score-engine-and-score-events-writeback.md` (this story: checkboxes, Dev Agent Record, Change Log, Status)
- `_bmad-output/implementation-artifacts/sprint-status.yaml` (4-4 → in-progress → review; last_updated 2026-07-10)

## Change Log

| Date | Change |
|---|---|
| 2026-07-10 | Story created (ready-for-dev) via bmad-create-story. |
| 2026-07-10 | Implemented `services/engine/confidence_score.py` (0–100 preparedness score, CS-1 ordering, CS-3 event binding, CS-4 no-contradiction, cold-start) + 20 tests. DB `score_events` writeback deferred to Epic 5 per product decision (AD-2). `pytest tests/engine/` → 147 passed, 6 skipped. Status → review. |
| 2026-07-10 | Code review (Epic 4 engine): AD-13 fix routed this module's explanation ₹ strings through `formatINR`. `pytest tests/engine/` → 148 passed, 6 skipped. Status → done. Review findings recorded in story 4-2. |
