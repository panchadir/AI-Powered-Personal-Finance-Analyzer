# Safe-to-Spend & Confidence — Test Scenario Suite (the engine quality gate)

**Created:** 2026-07-08
**Authors:** Amelia (engine), Winston (review), Murat (test architecture)
**Status:** Build-ready — this is the `services/engine/` pytest gate referenced by **PRD FR-4 AC / FR-5 AC** and **epic S4.2**.

> **Why this file exists.** The PRD, the epics, and the innovation-strategy roadmap all name "the 7 Wizard-of-Oz scenarios" as the single hard quality gate for the deterministic engine — but the scenarios were never written down (the problem-solving session paused at Step 4). This file enumerates them: **7 core scenarios + 6 boundary cases (13 total)**, each with exact inputs and expected outputs, so `test_safe_to_spend.py` can be table-driven and correct rather than invented under deadline. **No LLM computes any number here — this is deterministic Python, unit-tested.**

---

## Formula (of record)

```
safe_to_spend_today = max(0, (available_balance − reserved_total − buffer) ÷ days_until_next_confirmed_income)
```
Rounded **down** to the nearest ₹10 (never round a spend figure up). Two-layer display: **Today: ₹X** and **After confirmed income on {date}: ₹Y** — never present future income as today's money.

## Two design decisions this suite pins down (were latent/ambiguous)

**DD-1 — Reservation Rule (RR).** The problem-solving doc's literal "commitments inside the window are fully subtracted" would let a *known* commitment due before payday go unreserved if it sat outside its proximity window — a direct NFR-1 violation. Resolved for safety:

1. **Known commitment** (confirmed amount + due date) due **on-or-before** the next confirmed income → **always fully reserved**, regardless of proximity window. Safety beats precision.
2. **Predicted/uncertain commitment** (detected from history, amount/date estimated) → reserved **only once inside its criticality proximity window** (critical **7d** / medium **5d** / low **3d**); outside the window it **lowers Prediction Confidence and is surfaced**, but is not yet subtracted (don't over-restrict on a shaky far-out prediction).
3. **Variable-amount commitment** → reserve the **top of the range** (conservative-under-uncertainty).
4. A commitment **due on the income day** is reserved against current balance **unless** income confidence is High **and** income ≥ commitment (only then may the "after income" layer cover it).

**DD-2 — Buffer.** Default emergency floor **₹2,000**, configurable per user. Documented assumption to confirm during build; all scenarios below state the buffer explicitly.

## Evidence-pack output (what the engine returns and tests assert on)

```
{ reserved_total, spendable_pool (= balance − reserved − buffer),
  days_to_income, safe_to_spend_today, safe_to_spend_after_income (nullable),
  prediction_confidence (Low|Medium|High), drivers[], data_quality_flags[],
  safety_ok (bool: every commitment due before next income is covered) }
```

---

## Core scenarios (1–7)

| # | Scenario (tests) | Key inputs | reserved_total | pool | days | **STS today** | Pred. Conf. | Must-hold assertion |
|---|---|---|---|---|---|---|---|---|
| **1** | **Healthy mid-cycle** (baseline sanity) | bal ₹42,000; buffer ₹2,000; rent ₹15,000 due 1st (income day, known); EMI ₹8,500 due 5th (**after** income); salary 1st, 20d out | ₹15,000 | ₹25,000 | 20 | **₹1,250/day** | High | EMI due after income is **not** reserved against this cycle |
| **2** | **Critical inside 7-day window** (A-CRITICAL: never miss a committed obligation) | bal ₹22,000; buffer ₹2,000; rent ₹15,000 due 1st = 6d out (critical, within 7d); salary 1st, 6d | ₹15,000 | ₹5,000 | 6 | **₹830/day** | High | 6 × 830 = 4,980 ≤ 5,000 → rent **never** touchable |
| **3** | **Low balance, day before payday** (two-layer; never present tomorrow's money as today's) | bal ₹2,150; buffer ₹2,000; nothing due **today**; salary ₹55,000 tomorrow (1st), 1d | ₹0 (today layer) | ₹150 | 1 | **₹150** today; **After salary: ~₹990/day** | High | Today uses only confirmed present money; salary is a separate future layer |
| **4** | **Variable bill, top-of-range reserve** (conservative under uncertainty) | bal ₹28,000; buffer ₹2,000; electricity **₹1,500–₹3,000** due 22nd (medium, 4d, within 5d); rent ₹15,000 due 1st; salary 1st, 14d | ₹18,000 (15,000 + **3,000** top) | ₹8,000 | 14 | **₹570/day** | Medium | Reserves ₹3,000 not the ₹2,250 midpoint; midpoint would wrongly yield ₹625 |
| **5** | **Predicted, uncertain, outside window** (don't over-restrict; do flag) | bal ₹30,000; buffer ₹2,000; rent ₹15,000 due 1st (known); **detected** EMI ~₹5,000 due ~27th = 12d out (critical, **outside** 7d, single-history); salary 1st, 17d | ₹15,000 (EMI **not** yet locked) | ₹13,000 | 17 | **₹760/day** | Medium | EMI lowers Pred. Conf. + is surfaced ("an EMI-like ₹5,000 may be due ~27th — confirm and I'll protect it"); it becomes reserved once today enters its 7-day window |
| **6** | **Collision — many commitments before payday** (stacking) | bal ₹30,000; buffer ₹2,000; rent ₹15,000 (1st) + EMI ₹8,500 (30th, 3d) + broadband ₹800 (29th, 2d) — all before income; salary 1st, 5d | ₹24,300 | ₹3,700 | 5 | **₹740/day** | High | All three fully fenced; 5 × 740 = 3,700 ≤ pool; none missed |
| **7** | **Cold start / low data** (resolved-for-MVP: compute now, Low confidence, no fake 50) | ~20 days of history; salary ₹55,000 seen **once**; rent ₹15,000 detected once; bal ₹25,000; buffer ₹2,000; next income predicted 1st, ~10d | ₹15,000 (critical, reserved despite low conf) | ₹8,000 | 10 | **₹800/day** | **Low** | Computes immediately; Pred. Conf. Low **with reason** ("based on ~20 days; I assumed salary repeats on the 1st — confirm to sharpen"); no neutral-50 |

## Boundary cases (8–10)

| # | Boundary (tests) | Key inputs | reserved_total | pool | days | **STS today** | Must-hold assertion |
|---|---|---|---|---|---|---|---|
| **8** | **Due-date TODAY** (off-by-one guard) | bal ₹40,000; buffer ₹2,000; EMI ₹8,500 due **today** (5th, critical); next income 1st next month, 27d | ₹8,500 | ₹29,500 | 27 | **₹1,090/day** | A commitment due today is treated as **due** (fully reserved), never "0 days → ignore" |
| **9** | **Payday tomorrow + same-day commitment, uncertain income** (÷1 blow-up guard) | bal ₹18,000; buffer ₹2,000; rent ₹15,000 due tomorrow (income day); salary **Medium** confidence, 1d | ₹15,000 (income Medium → don't assume it covers same-day rent) | ₹1,000 | 1 | **₹1,000** | Same-day commitment reserved from present balance when income confidence < High; prevents the "÷1 → ₹16,000" over-payout |
| **10** | **Shortfall / would-be-negative** (never negative, never hidden) | bal ₹16,000; buffer ₹2,000; rent ₹15,000 + EMI ₹8,500 due before income = ₹23,500 | ₹23,500 | −₹9,500 | any | **₹0** (floored) | STS floored at ₹0 (never negative); honest shortfall surfaced ("committed bills before payday exceed your balance by ₹9,500 — here's what to do"); no crash |

## Additional boundary cases (11–13)

| # | Boundary (tests) | Key inputs | reserved_total | pool | days | **STS today** | Must-hold assertion |
|---|---|---|---|---|---|---|---|
| **11** | **Over-conservatism guard (FR-5.8)** — commitment-free, positive balance must yield non-zero STS | bal ₹30,000; buffer ₹2,000; **no commitments** due before next income; next income in 20d | ₹0 | ₹28,000 | 20 | **₹1,400/day** | STS must be > ₹0 when balance is positive and no commitments are due this cycle — ₹0 on these inputs is a **bug** (over-conservatism) |
| **12** | **Salary not detected (FR-4.8)** — no income credit identified in statement | bal ₹20,000; buffer ₹2,000; no transaction identified as salary; no confirmed income date | ₹0 (no commitments) | ₹18,000 | unknown | **N/A** | `safe_to_spend_after_income` = null; `data_quality_flags` includes `"no_income_detected"`; user-facing copy matches FR-4.8: "We couldn't detect a salary — add one manually?" — never a zero or crash |
| **13** | **Payday is today** (÷0 guard — the other half of the Seam's "0 or undefined" fallback; Scenario 12 already covers the `undefined` half) | bal ₹20,000; buffer ₹2,000; rent ₹15,000 due in 10 days (**after** today's income — not reserved this cycle); salary ₹55,000 confirmed **today**, High confidence; `days_until_next_confirmed_income` = **0** | ₹0 | ₹18,000 | 0 | **₹18,000** (reserved-only fallback — `days=0` is never used as a divisor) | Engine must never compute `pool ÷ 0`: no `ZeroDivisionError`, no `Infinity`/`NaN`, no crash. Falls back to reserved-only mode (`safe_to_spend_today = max(0, pool)`, undivided) — the same fallback path S4.2's AC names for `undefined`, now exercised for `0` |

---

## Confidence-Score companion assertions (FR-5)

Run alongside the Safe-to-Spend suite so the two indicators never contradict:

- **CS-1** Confidence Score reflects **preparedness only** — Scenario 6 (tight but covered) scores lower than Scenario 1 (comfortable), and **Scenario 10 (shortfall) scores lowest**; app-usage never moves it.
- **CS-2** Prediction Confidence tracks **data completeness** — High in S1/S2/S6, Medium in S4/S5, **Low in S7** — independent of the Score itself.
- **CS-3** Every score delta writes a `score_events` row with (`delta`, `trigger_event`, `explanation`, `suggested_action`). A score change with no matching row **fails the test** (event-to-explanation binding). Field names must match the data model exactly: `trigger_event` (not `triggering_event`) and `suggested_action` (not `action`).
- **CS-4** No contradiction: a scenario is invalid if Score says "well prepared" while Safe-to-Spend is ₹0 (S10 must show both low Score **and** ₹0, telling one story).

## Implementation note

Table-drive it: `@pytest.mark.parametrize` over the 13 rows above; assert each field of the evidence pack. `safety_ok` must be `True` for scenarios 1–9, 11, 12, and 13, and correctly `False`-with-honest-shortfall for 10. **Scenarios 12 and 13 together are the explicit test for the `days_until_next_confirmed_income` ÷0 guard named in `project-context.md`'s Seams section — 12 covers `undefined`, 13 covers `0`. Neither may be skipped; a payday-morning crash is the exact failure mode this pair exists to catch.** **This suite is the go/no-go for Day 2 — green before the dashboard is wired.**

*Generated by BMAD party-mode cross-functional review — clears the Critical blocker in the MVP-readiness Alignment Matrix (Problem-Solution doc → the 7 WoZ scenarios now exist in build-ready form).*
