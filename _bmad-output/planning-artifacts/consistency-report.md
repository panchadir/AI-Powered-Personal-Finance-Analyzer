# Cross-Document Consistency Audit — AI-Powered Personal Finance Analyzer

**Scope:** PRD (A) · Epics & Stories (B) · Safe-to-Spend Scenarios (C) · UX Spec (D) · Architecture Spine (E)
**Run at:** 2026-07-08
**Reviewer:** bmad-prd validate subagent (cross-document consistency checker)

---

## Fix Status Summary

| Finding | Severity | Status | Documents Changed |
|---|---|---|---|
| F-1 `safe_to_spend_after_salary` vs `after_income` | Critical | **FIXED** | prd.md §8 |
| F-2 Never-cut list protects ≥1, PRD requires ≥3 | High | **FIXED** | epics-and-stories.md never-cut list + cut order |
| F-3 "Step 1 of 3" framing absent from story ACs | High | **FIXED** | epics S2.4 AC; ux-spec enforcement checklist |
| F-4 `aria-disabled` on CTA absent from story ACs | High | **FIXED** | epics S2.4 AC |
| F-5 `trigger_event`/`suggested_action` field name conflict | Medium | **FIXED** | safe-to-spend-scenarios.md CS-3; ARCHITECTURE-SPINE.md AD-9 |
| F-6 DPDP Rule 4 no-pre-ticked-consent absent from S1.3 | Medium | **FIXED** | epics S1.3 AC |
| F-7 FR-1.9 aria-live auto-auth absent from S1.3 | Medium | **FIXED** | epics S1.3 AC |
| F-8 FR-5.7 30-day stale data banner absent from stories | Medium | **FIXED** | epics S5.1 AC |
| F-9 Over-conservatism guard test absent from scenario suite | Medium | **FIXED** | safe-to-spend-scenarios.md Scenario 11 added |
| F-10 Salary-not-detected state absent from scenario suite | Medium | **FIXED** | safe-to-spend-scenarios.md Scenario 12 added |
| F-11 FR-7.8 context handoff from Insights absent from stories | Medium | **FIXED** | epics S6.3 AC |
| F-12 FR-7.10 Copilot accessibility absent from stories | Medium | **FIXED** | epics S6.1 AC |
| F-13 FR-9.3 due_day=31 absent from S7.2 | Medium | **FIXED** | epics S7.2 AC |
| F-14 Persistent left nav absent from UX spec wireframes | Medium | **FIXED** | ux-spec-mvp.md enforcement checklist |
| F-15 S8.2 says "surface on dashboard"; Insights is its own page | Low | **FIXED** | epics S8.2 AC |
| F-16 UX spec upload missing "Step 1 of 3" (root: F-3) | Low | **FIXED** (via F-3) | ux-spec enforcement checklist |
| F-17 No Transactions Table wireframe in UX spec | Low | **DEFERRED** | Open item — ux-spec is intentionally minimal |
| F-18 `uploaded_files` absent from spine SQLite description | Low | **FIXED** | ARCHITECTURE-SPINE.md C4 container |
| F-19 Configurable buffer not tested in any scenario | Low | **DEFERRED** | Open item — parametrize Scenario 1 at build time |
| F-20 ERD doesn't detail `seen`/`dismissed` fields | Low | **DEFERRED** | Spine is intentionally high-level; PRD §7 is authoritative |

---

## Detailed Findings

### F-1 (Critical — FIXED) — `safe_to_spend_after_salary` vs `safe_to_spend_after_income`
**Documents:** PRD §8 API table (A) vs FR-4.12 engine struct (A) vs scenarios evidence pack (C) vs AD-8 (E)

The PRD's §8 API table used `safe_to_spend_after_salary` while FR-4.12, the Glossary, and the scenario file all used `safe_to_spend_after_income`. This would cause a guaranteed runtime `AttributeError` or `None` field in the dashboard integration.

**Fix applied:** PRD §8 `/dashboard` response field updated to `safe_to_spend_after_income`.

---

### F-2 (High — FIXED) — Never-cut list protected ≥1 detector; PRD FR-8.1 P0 requires ≥3
**Documents:** epics-and-stories.md never-cut list (B) vs prd.md FR-8.1 (A)

The developer's real-time decision rule under deadline pressure authorized cutting to 1 detector, which would fail a P0 requirement.

**Fix applied:** Never-cut list updated to "≥3 E8 insight detectors (S8.1, per FR-8.1 P0)". Cut order item 2 updated to "5 → 3 (never below 3)".

---

### F-3 (High — FIXED) — "Step 1 of 3" upload framing absent from all story ACs and UX spec
**Documents:** prd.md FR-2.5 (A) vs epics S2.4 (B) vs ux-spec-mvp.md (D)

FR-2.5 explicitly labels the step indicator a "functional onboarding contract, not decoration." With no story AC or UX spec enforcement item, a developer could ship without it and pass all written ACs.

**Fix applied:** S2.4 AC extended. UX spec enforcement checklist item #7 added.

---

### F-4 (High — FIXED) — `aria-disabled` on CTA absent from story ACs
**Documents:** prd.md FR-2.8 / NFR-8 (A) vs epics S2.4 (B)

`aria-disabled` vs `hidden` vs `disabled` are semantically different states. Without an explicit AC, developers default to `disabled` (removes from tab order) — failing FR-2.8 and NFR-8.

**Fix applied:** S2.4 AC extended with the `aria-disabled` requirement.

---

### F-5 (Medium — FIXED) — Field name conflict: `trigger_event`/`triggering_event` and `action`/`suggested_action`
**Documents:** prd.md FR-5.3 and §7 (A) vs ARCHITECTURE-SPINE.md AD-9 (E) vs safe-to-spend-scenarios.md CS-3 (C)

Two field names disagreed across the assertion document and the model definition, causing a guaranteed `AttributeError` in the CS-3 pytest assertion.

**Fix applied:** CS-3 assertion clarified to use `trigger_event` and `suggested_action` (matching the data model). AD-9 rule text updated to `trigger_event`.

---

### F-6–F-14 (Medium — FIXED) — Story ACs missing coverage for P0/P1 requirements
**Documents:** prd.md (A) vs epics-and-stories.md (B)

Nine story ACs were missing coverage for requirements that had no path to implementation without an explicit AC:

| Story | Added |
|---|---|
| S1.3 | DPDP Rule 4 (FR-1.7), auto-auth aria-live + 3s fallback (FR-1.9) |
| S2.4 | "Step 1 of 3" step indicator (FR-2.5), aria-disabled on CTA (FR-2.8/NFR-8) |
| S5.1 | 30-day stale data amber banner (FR-5.7) |
| S6.1 | role="log" + aria-live="polite" + aria-disabled send button (FR-7.10/NFR-8) |
| S6.3 | Context handoff chip + insight_id in POST body (FR-7.8) |
| S7.2 | due_day=31 → "end of month" edge case (FR-9.3) |

---

### F-9 (Medium — FIXED) — Over-conservatism guard test absent from scenario suite
**Documents:** prd.md FR-5.8 / §9 counter-metric (A) vs safe-to-spend-scenarios.md (C)

FR-5.8 explicitly requires a test that asserts STS > 0 on a positive-balance, commitment-free statement. All 10 original scenarios had at least one commitment.

**Fix applied:** Scenario 11 added: "Over-conservatism guard (FR-5.8)" with exact inputs (no commitments, positive balance) and expected non-zero STS output.

---

### F-10 (Medium — FIXED) — Salary-not-detected fallback absent from scenario suite
**Documents:** prd.md FR-4.8 (A) vs safe-to-spend-scenarios.md (C)

FR-4.8 defines the graceful fallback ("We couldn't detect a salary — add one manually?") but no scenario tested the zero-income-detection path.

**Fix applied:** Scenario 12 added: "Salary not detected (FR-4.8)" with expected `safe_to_spend_after_income=null` + `"no_income_detected"` data quality flag.

---

### F-15 (Low — FIXED) — S8.2 said "surface on dashboard"; Insights is a separate page
**Documents:** epics S8.2 (B) vs ARCHITECTURE-SPINE.md container view (E)

**Fix applied:** S8.2 AC updated to "surface on the Insights page."

---

### F-18 (Low — FIXED) — `uploaded_files` missing from spine SQLite container description
**Documents:** ARCHITECTURE-SPINE.md C4 container view (E) — internal inconsistency with its own ERD

**Fix applied:** `uploaded_files` added to the SQLite container description string.

---

## Deferred findings

| Finding | Reason deferred |
|---|---|
| F-17 — No Transactions Table wireframe in UX spec | ux-spec-mvp.md is intentionally a minimal north-star spec, not a full design system. FR-3.5 badge system and FR-3.7 virtual scroll are specified in the PRD. |
| F-19 — Configurable buffer not tested | Add a parametrized variant of Scenario 1 at build time, before merging to main. Low risk since all scenarios explicitly state buffer=₹2,000. |
| F-20 — ERD doesn't detail `seen`/`dismissed` fields | Architecture spine ERD is intentionally high-level. PRD §7 data model table is the authoritative schema and correctly specifies both fields. |

---

## Totals (pre-fix counts)
- Critical: 1 (F-1) — all fixed
- High: 3 (F-2, F-3, F-4) — all fixed
- Medium: 10 (F-5 through F-14) — all fixed
- Low: 6 (F-15 through F-20) — 3 fixed, 3 deferred
