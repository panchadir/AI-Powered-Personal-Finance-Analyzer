# Engine Contract — Safe-to-Spend & Confidence Score (LOCKED)

**Status:** LOCKED (2026-07-10) · **Owner story:** 4-1 (engine pre-flight) · **Implemented by:** 4-2 · **Asserted by:** 4-3 · **Extended by:** 4-4 (Confidence Score + score_events)

> This is the **single source of truth** for the deterministic financial engine. Stories 4-2 (engine) and 4-3 (pytest gate) build and assert against *this* document — not against paraphrases scattered across the PRD/epics. All numbers here are transcribed verbatim from [`safe-to-spend-scenarios.md`](../planning-artifacts/safe-to-spend-scenarios.md) and hand-verified (see §7). **No LLM computes any number in this engine (AD-1). Money is `Decimal`, never `float` (AD-8).**

---

## 1. Formula of record (AD-8 / FR-4.1)

```
safe_to_spend_today = max(0, (available_balance − reserved_total − buffer) ÷ days_until_next_confirmed_income)
```

- `max(0, …)` floor is **non-negotiable** — STS is never negative.
- Round **DOWN** to the nearest ₹10: `math.floor(x / 10) * 10`. **Rounding up is forbidden.** Every STS figure ends in `0`.
- `spendable_pool = available_balance − reserved_total − buffer` (may be negative internally; STS floors it).
- Two-layer output: **Today: ₹X** and **After confirmed income on {date}: ₹Y** — never merged, never present future income as today's money (FR-4.5).

### 1a. Denominator guard (`project-context.md` Seam — binding, extends AD-8)
`days_until_next_confirmed_income` may be **0** (payday is today — scenario 13) or **undefined/None** (no confirmed income — scenario 12). **Guard before dividing.** Never `ZeroDivisionError`, `Infinity`, or `NaN`.
- **Fallback (both cases):** reserved-only mode → `safe_to_spend_today = max(0, spendable_pool)` (undivided).
- Scenario 12 exercises the `undefined` path; scenario 13 exercises the `0` path. **Neither may be skipped** — this pair is the payday-morning crash guard.

---

## 2. Reservation Rule — DD-1 (FR-4.2, of record)

1. **Known commitment** (confirmed amount + due date) due **on-or-before** the next confirmed income → **always fully reserved**, regardless of proximity window. *Safety beats precision.*
2. **Predicted/uncertain commitment** (detected from history; amount/date estimated) → reserved **only once inside** its criticality proximity window; **outside** the window it **lowers Prediction Confidence and is surfaced** (a driver), but is **not** subtracted.
3. **Variable-amount commitment** → reserve the **top of the range** (conservative under uncertainty).
4. **Commitment due on the income day** → reserved against **current balance** **unless** income confidence is **High AND** income ≥ commitment (only then may the "after income" layer cover it).

### 2a. Criticality tiers & proximity windows (FR-4.3)
| Tier (enum) | Window | Reserve behavior | Scenario-file prose that maps here |
|---|---|---|---|
| `critical` | **7 days** | full amount subtracted immediately within window | "critical" |
| `important` (default) | **5 days** | ring-fenced with slight buffer | **"medium"** |
| `flexible` | **3 days** | shown as separate soft total | **"low"** |

> **DECISION (mapping lock):** the scenario file's prose "medium"/"low" are **not** enum values. The real enum is `critical | important | flexible` (`services/utils/enums.py`, default `important`). Disambiguated by window size: **medium → `important` (5d)**, **low → `flexible` (3d)**. 4-2 must construct `CommitmentInput.criticality` from the enum, never the prose word.

### 2b. Buffer — DD-2 (FR-4.4)
Default emergency floor **₹2,000**, per-user configurable. Every scenario states buffer explicitly. **OPEN ASSUMPTION → confirmed for MVP:** default ₹2,000, configurable field on the user record (wiring deferred; engine takes `buffer` as an input parameter so it is trivially overridable). See §8.

---

## 3. Engine input shape (4-2 implements)

Framework-agnostic; imports no `reflex`/`rx.*` (AD-1, AD-14). Money is `Decimal`.

```python
# services/engine/safe_to_spend.py
from dataclasses import dataclass
from decimal import Decimal
from datetime import date

@dataclass(frozen=True)
class CommitmentInput:
    name: str
    amount: Decimal                     # for a variable bill this is the TOP of range
    amount_min: Decimal | None = None   # set only for variable-amount commitments
    due_date: date | None = None
    criticality: str = "important"      # 'critical' | 'important' | 'flexible'
    is_predicted: bool = False          # True = detected-from-history (DD-1 rule 2)

@dataclass(frozen=True)
class EngineInput:
    available_balance: Decimal
    as_of: date                              # "today" — drives days_to_income & window math
    buffer: Decimal = Decimal("2000")        # DD-2 default; per-user configurable
    commitments: tuple[CommitmentInput, ...] = ()
    next_income_date: date | None = None     # None => no confirmed income (undefined guard)
    next_income_amount: Decimal | None = None
    income_confidence: str = "High"          # 'Low' | 'Medium' | 'High'
```

---

## 4. Evidence-pack output shape — FR-4.12 (4-3 asserts EVERY field by name)

```python
@dataclass(frozen=True)
class EvidencePack:
    reserved_total: Decimal
    spendable_pool: Decimal                       # = balance − reserved_total − buffer
    days_to_income: int | None                    # None => no confirmed income; 0 => payday today
    safe_to_spend_today: Decimal                  # max(0, …), floored down to nearest ₹10
    safe_to_spend_after_income: Decimal | None    # null when no income detected (FR-4.8 / scen 12)
    prediction_confidence: str                    # 'Low' | 'Medium' | 'High'
    drivers: tuple[str, ...]                       # human-readable reservation/surfacing drivers
    data_quality_flags: tuple[str, ...]           # e.g. 'no_income_detected'
    safety_ok: bool                               # True iff every commitment due <= next income covered
```

- Return a **frozen dataclass** (typed, immutable, asserted by attribute) — not a bare dict.
- `safe_to_spend_after_income` is `null`/`None` **only** when no income is detected (scenario 12). Otherwise it is the after-income per-day figure.
- **Persisted field-name lock (for 4-4):** the Confidence-Score write path uses `finance_app/models.py:ScoreEvent` columns **exactly** — `trigger_event` (NOT `triggering_event`) and `suggested_action` (NOT `action`) (AD-9, CS-3). Reference them via the model attribute, never a hardcoded string.

---

## 5. Frozen scenario table (13 rows) — copy verbatim into `test_safe_to_spend.py`

All amounts ₹. `days` = `days_to_income`. Buffer = ₹2,000 in every row unless noted. Full inputs live in [`safe-to-spend-scenarios.md`](../planning-artifacts/safe-to-spend-scenarios.md); this is the assertion contract.

### Core (1–7)
| # | Name | reserved_total | pool | days | **STS today** | after-income | Pred.Conf | safety_ok |
|---|---|---|---|---|---|---|---|---|
| 1 | Healthy mid-cycle | 15,000 | 25,000 | 20 | **1,250/day** | (n/a this cycle) | High | ✅ True |
| 2 | Critical inside 7-day window | 15,000 | 5,000 | 6 | **830/day** | — | High | ✅ True |
| 3 | Low balance, day before payday | 0 (today layer) | 150 | 1 | **150** today | **~990/day** after salary | High | ✅ True |
| 4 | Variable bill, top-of-range reserve | 18,000 (15,000 + **3,000** top) | 8,000 | 14 | **570/day** | — | **Medium** | ✅ True |
| 5 | Predicted, uncertain, outside window | 15,000 (EMI **not** locked) | 13,000 | 17 | **760/day** | — | **Medium** | ✅ True |
| 6 | Collision — many commitments before payday | 24,300 | 3,700 | 5 | **740/day** | — | High | ✅ True |
| 7 | Cold start / low data | 15,000 | 8,000 | 10 | **800/day** | — | **Low** | ✅ True |

### Boundary (8–13)
| # | Name | reserved_total | pool | days | **STS today** | after-income | safety_ok |
|---|---|---|---|---|---|---|---|
| 8 | Due-date TODAY (off-by-one guard) | 8,500 | 29,500 | 27 | **1,090/day** | — | ✅ True |
| 9 | Payday tomorrow + same-day commitment, uncertain income (÷1 guard) | 15,000 | 1,000 | 1 | **1,000** | — | ✅ True |
| 10 | Shortfall / would-be-negative | 23,500 | −9,500 | any | **0** (floored) | — | ❌ **False** + honest shortfall (short by ₹9,500) |
| 11 | Over-conservatism guard (FR-5.8) | 0 | 28,000 | 20 | **1,400/day** | — | ✅ True |
| 12 | Salary not detected (FR-4.8) | 0 | 18,000 | unknown | **N/A** | **null** + flag `no_income_detected` | ✅ True |
| 13 | Payday is today (÷0 guard) | 0 | 18,000 | **0** | **18,000** (reserved-only fallback, undivided) | — | ✅ True |

### Per-scenario must-hold assertions (transcribe into test IDs)
1. EMI due **after** income is not reserved this cycle.
2. `6 × 830 = 4,980 ≤ 5,000` → rent never touchable.
3. Today uses only confirmed present money; salary is a separate future layer (never merged).
4. Reserves **₹3,000** (top of range), not the ₹2,250 midpoint (midpoint would wrongly yield ₹625).
5. EMI lowers Pred.Conf. + is surfaced as a driver ("an EMI-like ₹5,000 may be due ~27th — confirm and I'll protect it"); becomes reserved once `as_of` enters its 7-day window.
6. All three commitments fully fenced; `5 × 740 = 3,700 ≤ pool`; none missed.
7. Computes immediately; Pred.Conf. **Low with reason** ("based on ~20 days; I assumed salary repeats on the 1st — confirm to sharpen"); **no neutral-50**.
8. A commitment due **today** is treated as **due** (fully reserved), never "0 days → ignore".
9. Same-day commitment reserved from **present balance** when income confidence < High → prevents "÷1 → ₹16,000" over-payout.
10. STS floored at ₹0 (never negative); honest shortfall surfaced ("committed bills before payday exceed your balance by ₹9,500 — here's what to do"); no crash.
11. STS **> ₹0** when balance positive and no commitments due this cycle — ₹0 here is a **bug** (over-conservatism).
12. `safe_to_spend_after_income = null`; `data_quality_flags` includes `"no_income_detected"`; copy = "We couldn't detect a salary — add one manually?"; never a zero or crash.
13. Never `pool ÷ 0`: no `ZeroDivisionError`/`Infinity`/`NaN`. Reserved-only fallback `safe_to_spend_today = max(0, pool)`, undivided.

### safety_ok truth table (complete — no gaps)
- **True:** 1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 12, 13
- **False (honest shortfall):** 10

---

## 6. Confidence-Score companion assertions (FR-5 — 4-4 implements, run alongside STS suite)

- **CS-1** — Score = **preparedness only**. Ordering: S6 (tight-but-covered) **<** S1 (comfortable); **S10 (shortfall) lowest**. App-usage never moves it.
- **CS-2** — Prediction Confidence = **data completeness**. **High** in S1/S2/S6, **Medium** in S4/S5, **Low** in S7. Independent of the Score.
- **CS-3** — Every score delta writes a `score_events` row `(delta, trigger_event, explanation, suggested_action)`. A change with **no matching row FAILS the test**. Field names exact: `trigger_event`, `suggested_action`.
- **CS-4** — **No contradiction:** invalid if Score says "well prepared" while STS is ₹0. S10 must show **low Score AND ₹0** (one story).

---

## 7. Self-check (hand-verified 2026-07-10)
Arithmetic on 3 rows confirms the source table (`STS = ⌊pool ÷ days ÷ 10⌋ × 10`):
- **S1:** 42,000 − 15,000 − 2,000 = 25,000; ⌊25,000/20/10⌋×10 = **1,250** ✓
- **S2:** 22,000 − 15,000 − 2,000 = 5,000; ⌊5,000/6/10⌋×10 = ⌊83.3⌋×10 = **830** ✓ (6×830 = 4,980 ≤ 5,000)
- **S6:** 30,000 − 24,300 − 2,000 = 3,700; ⌊3,700/5/10⌋×10 = **740** ✓ (5×740 = 3,700)
- **S4 (variable):** top-of-range 3,000 → reserved 18,000, pool 8,000, ⌊8,000/14/10⌋×10 = **570** ✓; midpoint 2,250 would give 8,750/14 = **625** (the bug the row guards against) ✓

`safety_ok` table covers all 13 rows with no gaps (§5).

---

## 8. Decisions & Open Assumptions

- **DECISION — scenario count locked at 13.** [`safe-to-spend-scenarios.md`](../planning-artifacts/safe-to-spend-scenarios.md) enumerates 13 (7 core + 6 boundary); **PRD FR-4 AC still says "12 total"** (7 core + 3 boundary + #11 + #12). The scenario file **and** epic story `4-3-...-all-13-scenarios` are authoritative. The delta is **scenario 13 (payday-is-today, `days=0` ÷0 guard)**, added after the PRD count was written. **Lock at 13.** *(Recommend a one-line PRD fix to FR-4 AC in a later docs pass; not blocking 4-2/4-3.)*
- **DECISION — criticality prose→enum mapping** (see §2a): medium→`important`, low→`flexible`. 4-2 uses the enum exclusively.
- **DECISION — engine returns a frozen dataclass** (`EvidencePack`), not a dict (§4).
- **DECISION — buffer default ₹2,000** confirmed for MVP (DD-2); passed as an `EngineInput` parameter so it is per-user overridable without touching engine logic. Persisting a per-user override is **out of scope for Epic 4** (belongs with commitments/settings UI).
- **OPEN — scenario 3 "After salary: ~₹990/day" is approximate** in the source. **Contract ruling:** 4-3 asserts the *today* layer exactly (**₹150**) and the *after-income* layer **within ±₹10** (one rounding bucket), OR pins the exact expected value once 4-2 fixes the salary-date/day-count inputs. 4-2 must record the exact computed after-income figure so 4-3 can tighten this to an exact assertion. Same tolerance note applies to scenario 5's "~₹5,000 EMI" surfaced-driver text (assert the flag/driver presence, not verbatim prose).
- **REQUIREMENT carried to 4-3 (AD-1):** `pytest services/engine/` must be green with **zero LLM calls**, enforced structurally by a fixture that injects an LLM client which **raises on construction/use** — so any accidental LLM reach fails loudly.

---

*Locked by story 4-1. Sources: `safe-to-spend-scenarios.md` (primary), `prd.md` FR-4/FR-5, `ARCHITECTURE-SPINE.md` AD-1/AD-8/AD-9, `project-context.md` Seams, `finance_app/models.py`, `services/utils/enums.py`.*
