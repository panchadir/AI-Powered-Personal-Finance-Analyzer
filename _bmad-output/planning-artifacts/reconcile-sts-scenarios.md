# Reconciliation: safe-to-spend-scenarios.md vs. PRD FR-4 ACs

**Input:** `safe-to-spend-scenarios.md` (10 scenarios — 7 core + 3 boundary, plus DD-1/DD-2 design decisions and evidence-pack output contract)
**Target:** PRD FR-4 ACs (FR-4.1–FR-4.8 + AC paragraph)
**Date:** 2026-07-08

---

## Gaps: in scenarios file, missing or unclear in FR-4 ACs

**Gap 1 — Zero-floor + honest shortfall surfacing (Scenario 10, boundary)**
Scenarios file requires STS floored at `max(0, …)` and a plain-language message ("committed bills before payday exceed your balance by ₹X — here's what to do") on shortfall. FR-4's formula (FR-4.1) and ACs do not mention the zero-floor, the shortfall message, or the `safety_ok=False` state. A builder reading FR-4 alone has no AC for this.

**Gap 2 — Rounding rule: floor to nearest ₹10 (Formula of record)**
The scenarios file mandates rounding *down* to the nearest ₹10 ("never round a spend figure up"). FR-4.1 states the formula but is entirely silent on rounding behavior. This affects every scenario's expected output and is unambiguous in the scenarios file but absent in the PRD.

**Gap 3 — Same-day income / income-confidence gate (DD-1 Rule 4, Scenario 9)**
A commitment due on the income day must be reserved from the *current* balance unless income confidence is High AND income ≥ commitment. FR-4.2 says only "commitments inside the window are fully subtracted regardless of confidence" — it does not address the income-day edge case, which is the guard against the "÷1 → ₹16,000 over-payout" failure mode.

**Gap 4 — Outside-window predicted commitments (DD-1 Rule 2, Scenario 5)**
Detected/predicted commitments outside their proximity window are *not* reserved but must lower Prediction Confidence and surface a confirmation prompt. FR-4.2 describes inside-window behavior only; outside-window treatment for uncertain commitments is absent from the ACs.

**Gap 5 — Evidence-pack output contract (all scenarios)**
The scenarios file defines a required engine output struct (`reserved_total`, `spendable_pool`, `days_to_income`, `safe_to_spend_today`, `safe_to_spend_after_income`, `prediction_confidence`, `drivers[]`, `data_quality_flags[]`, `safety_ok`). FR-4 ACs assert on scenario pass/fail but do not name or require this struct — a builder has no AC binding the output shape.

---

**Output file:** `c:\BMAD\AI-Powered-Personal-Finance-Analyzer\_bmad-output\planning-artifacts\reconcile-sts-scenarios.md`
