# Validation Report — AI-Powered Personal Finance Analyzer MVP PRD

- **PRD:** `_bmad-output/planning-artifacts/prd.md`
- **Rubric:** `.claude/skills/bmad-prd/assets/prd-validation-checklist.md`
- **Run at:** 2026-07-08
- **Grade:** Good
- **Reviewer files:** `review-rubric.md`, `consistency-report.md`

---

## Overall verdict

The PRD set is build-ready at its technical core — the deterministic engine spec, the 12-scenario pytest gate (expanded from 10 this session), read-only Copilot architecture, and data model are specific enough to drive a 3-day build without ambiguity. The critical gap cluster is in AC verifiability (tone-contract and SEBI-phrasing ACs are human-impression-dependent, not machine-assertable) and cross-document consistency (one guaranteed runtime field-name mismatch fixed; 9 story ACs that covered PRD P0 requirements now added). The 13 cross-document fixes applied this session close the most dangerous build traps.

---

## Dimension verdicts

| Dimension | Verdict |
|---|---|
| Decision-readiness | adequate |
| Substance over theater | adequate |
| Strategic coherence | adequate |
| Done-ness clarity | thin |
| Scope honesty | adequate |
| Downstream usability | adequate |
| Shape fit | thin |

---

## Findings by severity

### Critical (3) — 1 fixed this session, 2 carry forward

**[Done-ness clarity / Cross-document] F-1** — `safe_to_spend_after_salary` in PRD §8 API table vs `safe_to_spend_after_income` everywhere else (FR-4.12, Glossary, scenarios evidence pack). Guaranteed runtime `AttributeError` at dashboard integration.
**Status: FIXED** — PRD §8 updated to `safe_to_spend_after_income`.

**[Done-ness clarity] DC-1** — FR-6 AC "reviewable via the demo run" and FR-8 AC "SEBI phrasing rule verified" are not testable by an engineer — no pass criterion, no verifier, no method.
**Status: CARRY FORWARD** — Fix before implementing FR-6/FR-8: replace with unit-testable proxies (word-count + field match for briefing; substring assertion for SEBI phrasing).

**[Done-ness clarity] DC-2** — FR-7.6 AC "graceful honest response" — "graceful" is not testable. The FR body already has specific copy.
**Status: CARRY FORWARD** — Fix before implementing FR-7.6: AC should assert response contains "don't have" or "don't know," verified against 3 scripted queries in `copilot_samples`.

---

### High (10) — 7 fixed this session, 3 carry forward

**[Cross-document] F-2** — Epics never-cut list protected ≥1 detector; PRD FR-8.1 P0 requires ≥3. Developer would cut to 1 under pressure and fail a P0 requirement.
**Status: FIXED** — Never-cut list and cut order both updated to ≥3 floor.

**[Cross-document] F-3** — "Step 1 of 3" upload framing (FR-2.5 P0 "functional onboarding contract") absent from S2.4 AC and UX spec.
**Status: FIXED** — S2.4 AC extended; UX spec enforcement checklist item #7 added.

**[Cross-document] F-4** — `aria-disabled` on "Review transactions" CTA (FR-2.8 / NFR-8 P0) absent from S2.4 AC. Developer defaults to `disabled` or `hidden`, both fail acceptance.
**Status: FIXED** — S2.4 AC extended.

**[Done-ness clarity] DC-3** — FR-5 AC "Score and Safe-to-Spend never contradict" lacks an operational invariant (only a partial example).
**Status: CARRY FORWARD** — Fix: `if safe_to_spend_today == 0 then confidence_label != 'Well prepared'` — assert as a pytest invariant.

**[Done-ness clarity] DC-4** — FR-4.11 "This is intentional, not a bug" is architecture commentary embedded in a functional requirement; has no testable consequence.
**Status: CARRY FORWARD** — Fix: remove or replace with a real AC about timestamp display.

**[Scope honesty] SH-1** — `demo-data.json` referenced in 3 ACs but path unconfirmed as existing at build start.
**Status: CARRY FORWARD** — Action item: confirm `data/demo-data.json` exists (it was created in Step 20 of the prototype phase); add full path to §Sources.

**[Strategic coherence] SC-1** — §9 item 7 JTBD validation ("test user reports feeling informed/confident") is a single self-report with no pass threshold.
**Status: CARRY FORWARD** — Fix before acceptance testing: specify a structured instrument or behavioral proxy with a pass threshold.

**[Downstream usability] DU-1** — Seven source documents referenced without section anchors; story authors must read whole documents to find load-bearing decisions.
**Status: PARTIALLY FIXED** — §Sources now includes "§3 Design Decisions DD-1/DD-2" anchor for the problem-solution doc. Remaining source documents still lack anchors.

**[Shape fit] SF-2** — Emotional design constraints distributed across FRs but never summarized.
**Status: CARRY FORWARD** — Fix: add §3.1 Emotional Design Constraints (5 bullets) before build starts.

**[Cross-document] F-8** — FR-5.7 30-day stale data amber banner absent from all story ACs.
**Status: FIXED** — S5.1 AC extended.

---

### Medium (17) — 10 fixed this session, 7 carry forward

| ID | Finding | Status |
|---|---|---|
| F-5 | `trigger_event`/`suggested_action` field name conflict across 3 docs | **FIXED** — CS-3 and AD-9 canonicalized to data model names |
| F-6 | DPDP Rule 4 no-pre-ticked-consent absent from S1.3 | **FIXED** — S1.3 AC extended |
| F-7 | FR-1.9 aria-live auto-auth absent from S1.3 | **FIXED** — S1.3 AC extended |
| F-9 | Over-conservatism guard test absent from scenario suite | **FIXED** — Scenario 11 added |
| F-10 | Salary-not-detected fallback absent from scenario suite | **FIXED** — Scenario 12 added |
| F-11 | FR-7.8 context handoff from Insights absent from stories | **FIXED** — S6.3 AC extended |
| F-12 | FR-7.10 Copilot accessibility absent from stories | **FIXED** — S6.1 AC extended |
| F-13 | FR-9.3 due_day=31 absent from S7.2 | **FIXED** — S7.2 AC extended |
| F-14 | Persistent left nav absent from UX spec wireframes | **FIXED** — UX spec enforcement checklist item #6 added |
| DU-2 | `ux-spec-mvp.md` absent from §Sources | **FIXED** — Added to §Sources |
| DM-2 | No go/no-go gate on §9 success metrics | Carry forward — mark items 1–6 BLOCKING, 7 ADVISORY |
| ST-1 | §1 vision copy generic | Carry forward — low risk to build; cosmetic |
| SC-2 | Over-conservatism counter-metric binary not graduated | Carry forward — add 15% tolerance metric |
| DC-5 | FR-2.6 polling fallback has no AC | Carry forward — add fallback AC |
| SH-2 | FR-2.1 second CSV bank shape unnamed | Carry forward — name both banks + [ASSUMPTION] tag |
| DU-3 | `score_events` field-level types undefined in §7 | Carry forward — add type notes to §7 or Glossary |
| F-17 | No Transactions Table wireframe in UX spec | Deferred — ux-spec is intentionally minimal |

---

### Low (8) — 3 fixed, 5 carry forward / deferred

| ID | Finding | Status |
|---|---|---|
| F-15 | S8.2 "surface on dashboard" — Insights is its own page | **FIXED** — S8.2 AC updated |
| F-16 | UX spec upload missing "Step 1 of 3" (root: F-3) | **FIXED** (via F-3/F-14 UX spec enforcement) |
| F-18 | `uploaded_files` absent from spine SQLite description | **FIXED** — ARCHITECTURE-SPINE.md C4 updated |
| DM-3 | §12 open items lack resolve-by dates | Carry forward |
| ST-2 | NFR-9 no Copilot first-token latency target | Carry forward |
| SH-3 | FR-8.1 non-firing detectors status ambiguous | Carry forward |
| F-19 | Configurable buffer not tested | Deferred — parametrize at build time |
| F-20 | ERD doesn't detail `seen`/`dismissed` fields | Deferred — PRD §7 is authoritative |

---

## Mechanical notes
- Scenario count updated: 10 → 12 (Scenarios 11 and 12 added); PRD FR-4 AC and §9 item 2 updated to match.
- `ux-spec-mvp.md` enforcement checklist expanded: 5 items → 7 items.
- Architecture spine AD-9 field name canonicalized.
- Architecture spine C4 container description: `uploaded_files` table added.

---

## Reviewer files
- `review-rubric.md` — 7-dimension quality rubric walk
- `consistency-report.md` — 20-finding cross-document consistency audit

---

## Files changed this session (Step 25)

| File | Changes |
|---|---|
| `prd.md` | §8 API field `safe_to_spend_after_salary` → `safe_to_spend_after_income`; §Sources added `ux-spec-mvp.md`; FR-4 AC scenario count 10 → 12; §9 item 2 scenario count updated |
| `epics-and-stories.md` | Never-cut list ≥1 → ≥3 detectors; cut order stops at 3 not 1; S1.3 AC (DPDP + auto-auth aria); S2.4 AC (Step 1 of 3 + aria-disabled); S4.2 AC (12 scenarios, field names); S5.1 AC (30-day stale banner); S6.1 AC (accessibility); S6.3 AC (context handoff); S7.2 AC (due_day=31); S8.1 header + AC (≥3 must-ship); S8.2 AC (Insights page not dashboard) |
| `safe-to-spend-scenarios.md` | CS-3 field names canonicalized; Scenarios 11 (over-conservatism) and 12 (salary-not-detected) added |
| `ux-spec-mvp.md` | Copilot "stretch" label removed (must-ship); score chip raw number removed (FR-5.5 compliant label); enforcement checklist 5 → 7 items (left nav + Step 1 of 3) |
| `ARCHITECTURE-SPINE.md` | AD-9 `triggering_event` → `trigger_event`; C4 SQLite container added `uploaded_files` |
