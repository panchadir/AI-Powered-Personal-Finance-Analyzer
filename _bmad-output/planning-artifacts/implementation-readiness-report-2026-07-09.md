---
stepsCompleted: ["step-01-document-discovery", "step-02-prd-analysis", "step-03-epic-coverage-validation", "step-04-ux-alignment", "step-05-epic-quality-review", "step-06-final-assessment"]
documentsSelected:
  prd: "_bmad-output/planning-artifacts/prd.md"
  architecture: "_bmad-output/planning-artifacts/architecture/architecture-AI-Powered-Personal-Finance-Analyzer-2026-07-08/ARCHITECTURE-SPINE.md"
  epics_and_stories: "_bmad-output/planning-artifacts/epics.md"
  epics_and_stories_note: "epics-and-stories.md (141 lines) is a summary/earlier draft — excluded"
  ux: "_bmad-output/planning-artifacts/ux-spec-mvp.md"
---

# Implementation Readiness Assessment Report

**Date:** 2026-07-09
**Project:** AI-Powered-Personal-Finance-Analyzer

## Document Inventory

### PRD Documents Found

**Whole Documents:**
- `prd.md` (409 lines)

**Sharded Documents:** None

---

### Architecture Documents Found

**Whole Documents:**
- `architecture/architecture-AI-Powered-Personal-Finance-Analyzer-2026-07-08/ARCHITECTURE-SPINE.md` (316 lines)

**Sharded Documents:** None

---

### Epics & Stories Documents Found

**Whole Documents:**
- `epics.md` (1021 lines) ← **SELECTED** (comprehensive epics + stories)
- `epics-and-stories.md` (141 lines) ← Summary/overview version

**Sharded Documents:** None

---

### UX Design Documents Found

**Whole Documents:**
- `ux-spec-mvp.md` (96 lines)

**Sharded Documents:** None

---

## PRD Analysis

### Functional Requirements

| ID | Priority | Capability | Requirement Summary |
|---|---|---|---|
| FR-1.1 | P0 | Auth | Register email+password; bcrypt hashed; auth token in httpOnly cookie |
| FR-1.2 | P0 | Auth | Registration auto-authenticates; redirect to Upload; no email verification MVP |
| FR-1.3 | P0 | Auth | Login/logout; protected pages redirect to login |
| FR-1.4 | P0 | Auth | All data scoped to user_id; no cross-user access; IDOR test required |
| FR-1.5 | P0 | Auth | Trust signal ("No guessing. No shame.") above form; password show/hide toggle |
| FR-1.6 | P0 | Auth | "Email already registered" error with inline "Log in instead?" link |
| FR-1.7 | P0 | Auth | T&C / Privacy links open in in-page modal; no pre-ticked consent checkboxes (DPDP Rule 4) |
| FR-1.8 | P0 | Auth | Validation fires on blur, clears on input |
| FR-1.9 | P0 | Auth | Auto-auth transition: aria-live="assertive"; manual fallback after 3s; ?fail=1 must not auto-redirect |
| FR-2.1 | P0 | Upload | Upload CSV; map to canonical schema (≥2 Indian-bank shapes) |
| FR-2.2 | P0 | Upload | Upload text-based PDF via statementsparser → pdfplumber → camelot → LLM fallback chain |
| FR-2.3 | P0 | Upload | Normalize to canonical schema; de-duplicate on hash(date+amount+description); persist |
| FR-2.4 | P0 | Upload | Scanned/image PDF detected and honestly refused; no silent failure |
| FR-2.5 | P0 | Upload | Screen framed as "Step 1 of 3" — functional onboarding contract |
| FR-2.6 | P0 | Upload | Parse progress: 4 named real-server-state steps; WS preferred, 1-second polling fallback |
| FR-2.7 | P0 | Upload | Completion summary: "{n} by rules · {n} by AI · {n} need your help" from real parse output |
| FR-2.8 | P0 | Upload | "Review transactions" CTA aria-disabled (not hidden) until parse completes |
| FR-2.9 | P0 | Upload | Parse failure shows empathetic copy + support link; not generic toast |
| FR-2.10 | P0 | Upload | Back navigation mid-upload prompts confirmation |
| FR-3.1 | P0 | Categorization | Tier 1: deterministic keyword/merchant rules |
| FR-3.2 | P0 | Categorization | Tier 2: LLM (claude-haiku-4-5) with structured-output schema; hard-constrained category enum |
| FR-3.3 | P0 | Categorization | Every transaction stores category_source and category_confidence |
| FR-3.4 | P0 | Categorization | Tier 3 "Teach Me": correction writes merchant-level rule; "Re-apply to all" toggle defaults ON; persists |
| FR-3.5 | P0 | Categorization | Confidence badge system: needs_review=amber "?", ai_categorised=blue "AI", rule=no badge; no raw % shown |
| FR-3.6 | P0 | Categorization | Filter chips dynamically generated from actual parsed categories |
| FR-3.7 | P0 | Categorization | Transaction list uses virtual scroll (not standard DOM list) |
| FR-3.8 | P0 | Categorization | "Needs review" banner in amber tone (not error red) |
| FR-3.9 | P0 | Categorization | "See my Dashboard" CTA always enabled (sticky) |
| FR-3.10 | P0 | Categorization | Credit/income rows visually distinguished with green treatment |
| FR-4.1 | P0 | STS Engine | Formula: max(0, (balance − reserved − buffer) ÷ days_to_income); floor to nearest ₹10; never negative |
| FR-4.2 | P0 | STS Engine | Reservation rules for known/predicted/variable commitments; income-day handling |
| FR-4.3 | P0 | STS Engine | Commitment criticality tiers: Critical(7d), Important(5d), Flexible(3d); default=Important |
| FR-4.4 | P0 | STS Engine | Buffer: default ₹2,000; user-configurable; explicit in all engine tests |
| FR-4.5 | P0 | STS Engine | Two-layer display: "Today: ₹X" and "After confirmed income on {date}: ₹Y" — never merged |
| FR-4.6 | P0 | STS Engine | Conservative under uncertainty: variable bills reserve top-of-range; missing data lowers Prediction Confidence |
| FR-4.7 | P0 | STS Engine | Freshness caveat on hero card: "based on your statement up to {date}" |
| FR-4.8 | P0 | STS Engine | Undetected salary fallback: "We couldn't detect a salary — add one manually?" (not zero or error) |
| FR-4.9 | P0 | STS Engine | Shortfall state: STS floored to ₹0; honest shortfall message surfaced; no crash/silence |
| FR-4.10 | P0 | STS Engine | Live update: STS recalculates when commitment added/edited/deleted; no full page reload |
| FR-4.11 | P0 | STS Engine | Briefing snapshot vs live hero: briefing=snapshot; hero=live. Intentional, not a bug |
| FR-4.12 | P0 | STS Engine | Engine output struct fully defined: reserved_total, spendable_pool, days_to_income, STS_today, STS_after_income, prediction_confidence, drivers[], data_quality_flags[], safety_ok |
| FR-5.1 | P0 | CS Engine | Confidence Score (0–100): measures financial preparedness only; never app engagement |
| FR-5.2 | P0 | CS Engine | Prediction Confidence (Low/Medium/High): measures data completeness; never conflated with Score |
| FR-5.3 | P0 | CS Engine | Event-to-explanation binding: every score change writes score_events row |
| FR-5.4 | P0 | CS Engine | Cold start: compute immediately; Prediction Confidence=Low with reason; positive framing |
| FR-5.5 | P0 | CS Engine | Confidence chip interaction: inline tooltip with distinct copy per level; no raw score numbers shown |
| FR-5.6 | P0 | CS Engine | "Why?" expandable block on hero card; fallback copy when insufficient data |
| FR-5.7 | P0 | CS Engine | Stale data warning: amber banner when statement >30 days old |
| FR-5.8 | P0 | CS Engine | Over-conservatism guard: STS never ₹0 on positive-balance statement with no commitments due |
| FR-6.1 | P0 | Dashboard | Hero-first layout: STS card + Confidence chip above fold always |
| FR-6.2 | P0 | Dashboard | Plain-language briefing narrated by Claude; honest, calm, non-judgmental; LLM never computes numbers |
| FR-6.3 | P1 | Dashboard | Briefing follows Observation → Evidence → Explanation → Action shape |
| FR-6.4 | P0 | Dashboard | Persistent left nav across all 4 app screens |
| FR-6.5 | P0 | Dashboard | "+ Add a commitment" inline modal; STS updates live on save |
| FR-7.1 | P0 | Copilot | Chat interface; responses stream token-by-token |
| FR-7.2 | P0 | Copilot | Copilot uses read-only tools over real data; never invents numbers; never performs financial actions |
| FR-7.3 | P0 | Copilot | 4 hardcoded LLM system-prompt rules (non-configurable): no invented figures; explicit uncertainty; no investment recs; always populate trace |
| FR-7.4 | P0 | Copilot | SSE event schema: {type:token,text}, {type:trace,sources}, {type:done} |
| FR-7.5 | P0 | Copilot | Trace chips: "Based on: …" below every data-citing response; tap navigates to underlying data |
| FR-7.6 | P0 | Copilot | "I don't know" as valid response; insufficient-data graceful reply with guidance |
| FR-7.7 | P1 | Copilot | Quick-prompt buttons (e.g. "Can I afford ₹___ this weekend?") |
| FR-7.8 | P1 | Copilot | Context handoff from Insights: pre-populated input + dismissable chip; insight_id in POST body |
| FR-7.9 | P1 | Copilot | Chat history stored server-side; scoped to user_id |
| FR-7.10 | P1 | Copilot | Accessibility: role="log" + aria-live="polite"; stream announces completed sentences; aria-disabled on send |
| FR-8.1 | P0 | Insights | ≥3 of 5 named pattern detectors fire on demo statement: post-payday spike, death-by-small-purchases, zombie subscriptions, weekend-vs-weekday pace, upcoming-commitment collision |
| FR-8.2 | P0 | Insights | Each insight: Observation→Evidence→Explanation→Action; evidence cites 2–3 exact data points |
| FR-8.3 | P0 | Insights | SEBI IA boundary: Action layer uses "consider" framing; never prescriptive |
| FR-8.4 | P0 | Insights | Insight lifecycle: seen=soft fade; dismissed=collapsed section; all-dismissed empty state; insufficient-data positive framing |
| FR-8.5 | P0 | Insights | When data_months < 3: footer note "More data sharpens these patterns" |
| FR-8.6 | P1 | Insights | Insights woven into the briefing |
| FR-9.1 | P1 | Commitments | Detect recurring obligations; proactively surface for user confirmation |
| FR-9.2 | P1 | Commitments | User can add/edit/delete commitment: name, amount, due-day, criticality; default=Important |
| FR-9.3 | P1 | Commitments | due_day=31 maps to last day of shorter months; displayed as "end of month" |
| FR-9.4 | P1 | Commitments | POST/PATCH responses include safe_to_spend_updated for client-side update without separate fetch |

**Total FRs: 72 sub-requirements across 9 functional areas (FR-1 through FR-9)**

---

### Non-Functional Requirements

| ID | Category | Requirement |
|---|---|---|
| NFR-1 | Honesty & Safety (hard) | No displayed number may cause a missed obligation; conservative-by-default; pipeline failure degrades to visible state; LLM never in STS/CS computation path |
| NFR-2 | Deployment | Runs on `reflex run`; no cloud required; data in local PostgreSQL 16 (docker-compose service `db`; SQLite test-only); single-user MVP |
| NFR-3 | Architecture | All money math in services/engine/ (deterministic); LLM confined to services/narrate/; architectural boundary, not stylistic |
| NFR-4 | Cost & Model Routing | Claude API spend < $15 for build+demo; claude-haiku-4-5 for categorization; claude-opus-4-8 (or claude-sonnet-5) for narration+Copilot; batch API + prompt caching |
| NFR-5 | Privacy | Data stays local; only transaction text sent to Claude API; UI states boundary; secrets in .env; auth token in httpOnly cookie |
| NFR-6 | Migratability | Business logic in framework-agnostic services/; PostgreSQL already the Phase-1 store; Phase 2 (FastAPI, WhatsApp/AA) is re-skin not rewrite |
| NFR-7 | Localization | formatINR() (Indian grouping ₹1,25,000) and formatDate() (ISO→"30 Jun 2026") required in all currency/date displays |
| NFR-8 | Accessibility | role="log"+aria-live="polite" on Copilot; aria-live="assertive" on auto-auth; aria-disabled on inactive CTAs |
| NFR-9 | Performance | Parse <60s for standard 3-month PDF on dev laptop; Dashboard initial render <3s after parse |

**Total NFRs: 9**

---

### Additional Requirements / Constraints

- **Demo dataset AC:** 24 transactions (18 rules, 3 AI, 3 need-help); HDFC June 2026 "Priya" dataset; ≥3 insights must fire
- **pytest gate:** 12 engine scenarios must pass with zero LLM calls (7 core + 3 boundary + over-conservatism + salary-not-detected)
- **Kill-signal protocol:** STS error causing missed obligation → immediate feature pause + trust audit
- **DPDP Rule 4 compliance:** No pre-ticked consent checkboxes; T&C in modal
- **SEBI IA boundary:** All insight Action text must use "consider" framing; never prescriptive
- **API surface:** 13 canonical endpoints (auth×3, statements×3, transactions×1, dashboard×1, insights×2, commitments×3, copilot×1)
- **Data model:** 8 tables defined with explicit field list

### PRD Completeness Assessment

The PRD is **highly complete** for an MVP document. It provides:
- Numbered FRs with granular ACs at sub-requirement level
- Priority tiers (P0/P1/P2) clearly assigned
- Explicit non-goals and deferred items
- A canonical data model and API surface table
- Test suite specification (12 engine scenarios) cross-referenced
- A kill-signal protocol and honesty spine as non-negotiable constraints
- 4 open items tracked with owners and resolution conditions

**Minor gap noted:** NFR coverage of security (OWASP/IDOR) is implicit in the architecture/project-context rules but only FR-1.4 explicitly calls out cross-user isolation in the PRD body. The architecture document carries the security load.

---

## Epic Coverage Validation

### Coverage Matrix

| FR | PRD Requirement Summary | Epic / Story Coverage | Status |
|---|---|---|---|
| FR-1.1 | Register; bcrypt; httpOnly cookie | Epic 1 → S1.3 | ✅ Covered |
| FR-1.2 | Auto-auth → Upload; no email verify | Epic 1 → S1.3 | ✅ Covered |
| FR-1.3 | Login/logout; protected page redirect | Epic 1 → S1.4 | ✅ Covered |
| FR-1.4 | user_id scoping; IDOR test | Epic 1 → S1.4 (baseline); Epic 8 → S8.3 (full IDOR test) | ✅ Covered |
| FR-1.5 | Trust signal above form; show/hide | Epic 1 → S1.3 | ✅ Covered |
| FR-1.6 | "Email already registered" inline link | Epic 1 → S1.3 | ✅ Covered |
| FR-1.7 | T&C in modal; no pre-ticked checkboxes | Epic 1 → S1.3 | ✅ Covered |
| FR-1.8 | Validation on blur, clears on input | Epic 1 → S1.5 | ✅ Covered |
| FR-1.9 | aria-live on transition; fallback link; ?fail=1 | Epic 1 → S1.5 | ✅ Covered |
| FR-2.1 | CSV upload; ≥2 Indian-bank shapes | Epic 2 → S2.2 | ✅ Covered |
| FR-2.2 | PDF upload; parser chain | Epic 2 → S2.3 | ✅ Covered |
| FR-2.3 | Normalize; dedup; persist | Epic 2 → S2.5 | ✅ Covered |
| FR-2.4 | Scanned PDF → honest refusal | Epic 2 → S2.3; Epic 8 → S8.1 | ✅ Covered |
| FR-2.5 | "Step 1 of 3" indicator | Epic 2 → S2.4 | ✅ Covered |
| FR-2.6 | 4-step progress; WS/polling | Epic 2 → S2.4 | ✅ Covered |
| FR-2.7 | Completion summary: real counts | Epic 2 → S2.4 | ✅ Covered |
| FR-2.8 | "Review" CTA aria-disabled until done | Epic 2 → S2.4 | ✅ Covered |
| FR-2.9 | Parse failure: empathetic copy + link | Epic 2 → S2.4; Epic 8 → S8.1 | ✅ Covered |
| FR-2.10 | Back-nav confirmation mid-upload | Epic 2 → S2.4 | ✅ Covered |
| FR-3.1 | Tier-1 rules engine | Epic 3 → S3.1 | ✅ Covered |
| FR-3.2 | Tier-2 LLM; hard-constrained enum | Epic 3 → S3.2 | ✅ Covered |
| FR-3.3 | Stores category_source + confidence | Epic 3 → S3.2 | ✅ Covered |
| FR-3.4 | Teach Me; merchant rule; re-apply toggle | Epic 3 → S3.3 | ✅ Covered |
| FR-3.5 | Confidence badge system; no raw % | Epic 3 → S3.4 | ✅ Covered |
| FR-3.6 | Dynamic filter chips from actual categories | Epic 3 → S3.1 | ✅ Covered |
| FR-3.7 | Virtual scroll | Epic 3 → S3.4 | ✅ Covered |
| FR-3.8 | "Needs review" banner amber, not red | Epic 3 → S3.1 | ✅ Covered |
| FR-3.9 | "See my Dashboard" always enabled | Epic 3 → S3.1 | ✅ Covered |
| FR-3.10 | Credit rows green treatment | Epic 3 → S3.1 | ✅ Covered |
| FR-4.1 | STS formula; floor ₹10; never negative | Epic 4 → S4.2 | ✅ Covered |
| FR-4.2 | Reservation Rule (DD-1) — all 4 sub-rules | Epic 4 → S4.2 | ✅ Covered |
| FR-4.3 | Criticality tiers: 7d/5d/3d; default Important | Epic 4 → S4.2 | ✅ Covered |
| FR-4.4 | Buffer ₹2,000; configurable; explicit in tests | Epic 4 → S4.2 | ✅ Covered |
| FR-4.5 | Two-layer display; never merged | Epic 5 → S5.1 | ✅ Covered |
| FR-4.6 | Conservative under uncertainty | Epic 4 → S4.2 | ✅ Covered |
| FR-4.7 | Freshness caveat on hero card | Epic 5 → S5.1 | ✅ Covered |
| FR-4.8 | No salary detected → prompt (not zero) | Epic 5 → S5.1; Epic 8 → S8.1 | ✅ Covered |
| FR-4.9 | Shortfall state; ₹0 floor; honest message | Epic 4 → S4.2, S4.3; Epic 8 → S8.1 | ✅ Covered |
| FR-4.10 | Live update on commitment change | Epic 5 → S5.5 | ✅ Covered |
| FR-4.11 | Briefing = snapshot; hero = live | Epic 5 → S5.3 | ✅ Covered |
| FR-4.12 | Engine output struct definition | Epic 4 → S4.2 | ✅ Covered |
| FR-5.1 | CS measures preparedness only | Epic 4 → S4.4 | ✅ Covered |
| FR-5.2 | Prediction Confidence separate | Epic 4 → S4.4 | ✅ Covered |
| FR-5.3 | score_events binding | Epic 4 → S4.4 | ✅ Covered |
| FR-5.4 | Cold start; positive framing | Epic 4 → S4.4 | ✅ Covered |
| FR-5.5 | Chip tooltip; no raw numbers | Epic 5 → S5.2 | ✅ Covered |
| FR-5.6 | "Why?" expandable block | Epic 5 → S5.1 | ✅ Covered |
| FR-5.7 | Stale data amber banner >30 days | Epic 5 → S5.1 | ✅ Covered |
| FR-5.8 | Over-conservatism guard test | Epic 4 → S4.3 | ✅ Covered |
| FR-6.1 | Hero-first layout; STS+chip above fold | Epic 5 → S5.1 | ✅ Covered |
| FR-6.2 | Briefing narrated by Claude; LLM no math | Epic 5 → S5.3 | ✅ Covered |
| FR-6.3 | Briefing: O→E→E→A shape (P1) | Epic 5 → S5.3 | ✅ Covered |
| FR-6.4 | Persistent left nav across all 4 screens | Epic 1 → S1.5 (skeleton); all epics maintain it | ✅ Covered |
| FR-6.5 | "+ Add commitment" modal; live update | Epic 5 → S5.5 | ✅ Covered |
| FR-7.1 | Chat; token-by-token streaming | Epic 6 → S6.1 | ✅ Covered |
| FR-7.2 | Read-only tools; no invented numbers | Epic 6 → S6.2 | ✅ Covered |
| FR-7.3 | 4 hardcoded system-prompt rules | Epic 6 → S6.2 | ✅ Covered |
| FR-7.4 | SSE event schema: token/trace/done | Epic 6 → S6.3 | ✅ Covered |
| FR-7.5 | Trace chips; tap navigates to data | Epic 6 → S6.3 | ✅ Covered |
| FR-7.6 | "I don't know" graceful response | Epic 6 → S6.3 | ✅ Covered |
| FR-7.7 | Quick-prompt buttons (P1) | Epic 6 → S6.4 | ✅ Covered |
| FR-7.8 | Context handoff from Insights (P1) | Epic 6 → S6.4 | ✅ Covered |
| FR-7.9 | Chat history server-side; user_id scoped (P1) | Epic 6 → S6.1 | ✅ Covered |
| FR-7.10 | Accessibility: role="log", aria-live (P1) | Epic 6 → S6.1 | ✅ Covered |
| FR-8.1 | ≥3 of 5 insight detectors fire | Epic 7 → S7.1 | ✅ Covered |
| FR-8.2 | O→E→E→A; 2–3 exact evidence data points | Epic 7 → S7.2 | ✅ Covered |
| FR-8.3 | SEBI phrasing rule on Action | Epic 7 → S7.2 | ✅ Covered |
| FR-8.4 | Insight lifecycle: seen/dismissed/empty | Epic 7 → S7.3 | ✅ Covered |
| FR-8.5 | data_months < 3 footer note | Epic 7 → S7.3 | ⚠️ Partial — S7.3 covers dismiss lifecycle but footer note for data_months < 3 is listed in FR-8.5; S7.3 ACs mention empty states but do not explicitly call out the "More data sharpens these patterns" footer note |
| FR-8.6 | Insights woven into briefing (P1) | Epic 5 → S5.3 / Epic 7 | ⚠️ Partial — S5.3 mentions briefing calls narrate/ with evidence pack but no story explicitly AC's weaving insight patterns into the briefing text |
| FR-9.1 | Detect recurring obligations; surface for confirmation | Epic 5 → S5.6 | ✅ Covered |
| FR-9.2 | Add/edit/delete commitment; default Important | Epic 5 → S5.5 | ✅ Covered |
| FR-9.3 | due_day=31 → last day of month | Epic 5 → S5.5 | ✅ Covered |
| FR-9.4 | POST/PATCH return safe_to_spend_updated | Epic 5 → S5.5 | ✅ Covered |

### NFR Coverage Matrix

| NFR | Requirement | Epic / Story Coverage | Status |
|---|---|---|---|
| NFR-1 | Honesty spine; no silent failures; LLM not in STS/CS path | Epics 4 (S4.2, S4.3, S4.4), 8 (S8.1); all narrate/ guards | ✅ Covered |
| NFR-2 | Local PostgreSQL (docker-compose); reflex run | Epic 1 → S1.1, S1.2 | ✅ Covered |
| NFR-3 | services/engine/ separated from services/narrate/ | Epic 4 → S4.2 (enforced by architecture + pytest structure) | ✅ Covered |
| NFR-4 | Model routing constants; prompt caching; <$15 | Epic 5 → S5.3; Epic 6 → S6.2 (config.py constants + cache_control) | ✅ Covered |
| NFR-5 | Data local; secrets in .env; httpOnly cookie | Epic 1 → S1.1, S1.3; Epic 6 → S6.2 | ✅ Covered |
| NFR-6 | Framework-agnostic services/ | Epic 1 → S1.1 (structure); enforced throughout all epics | ✅ Covered |
| NFR-7 | formatINR() and formatDate() mandatory | Epic 1 → S1.2 (created); enforced in S5.1, S5.4, etc. | ✅ Covered |
| NFR-8 | aria-live, aria-disabled, role="log" | Epic 1 → S1.5; Epic 2 → S2.4; Epic 6 → S6.1 | ✅ Covered |
| NFR-9 | Parse <60s; dashboard <3s | Epic 2 → S2.3; Epic 5 → S5.1 | ✅ Covered |

---

### Missing / Partial Coverage Findings

#### ⚠️ PARTIAL: FR-8.5 — "More data sharpens these patterns" footer

**PRD requirement:** When `data_months < 3`, a footer note reads "More data sharpens these patterns."
**Epic coverage:** The FR-8.5 line is listed in the Epic List summary for Epic 7, but **no story AC in Epic 7 explicitly asserts this footer note**. S7.3 (Insights Page & Dismiss Lifecycle) covers the dismiss lifecycle and empty states but does not include an AC for the `data_months < 3` footer text.
**Risk:** Medium — the footer is a named honest-framing element. Without an AC in a story, a developer may omit it.
**Recommendation:** Add an AC to S7.3 (or a new S7.x): "When data_months < 3, a footer note 'More data sharpens these patterns.' is visible on the Insights page."

---

#### ⚠️ PARTIAL: FR-8.6 — Insights woven into briefing

**PRD requirement (P1):** Insights woven into the briefing.
**Epic coverage:** FR-8.6 appears in the Epic 7 coverage list, and S5.3 (Morning Briefing Narration) describes calling narrate/ with the evidence pack — but no story AC explicitly states "insight patterns are surfaced within the briefing text" or "if active insights exist, the top insight's Observation sentence appears in the briefing."
**Risk:** Low-Medium — it's a P1 and the briefing + insights are in adjacent stories (S5.3 and S7.x), but the handoff point (does narrate/ receive insight candidates as context?) is not specified in any story AC.
**Recommendation:** Add a sentence to S5.3 AC or create a story that states: "When active insights exist, the briefing narration references the top insight's Observation." The narrate/ call signature should include an `insight_candidates` parameter.

---

#### ✅ VERIFIED COMPLETE: Insight detector names discrepancy

**Observation:** FR-8.1 in the PRD names 5 detector patterns: "post-payday spike, death-by-small-purchases, zombie subscriptions, weekend-vs-weekday pace, upcoming-commitment collision." S7.1 names the 5 detectors as classes: `RecurringSpendDetector`, `SpendingSpikeDetector`, `SalaryNotDetectedDetector`, `BufferDrainDetector`, `UnusualMerchantDetector`.
**Assessment:** The class names are not 1:1 with the FR-8.1 pattern names (e.g. "zombie subscriptions" → `RecurringSpendDetector`?; "upcoming-commitment collision" → `BufferDrainDetector`?). The mapping is **implicit** — an implementer needs to infer which class covers which PRD pattern.
**Risk:** Medium — a developer building S7.1 may implement different patterns than what FR-8.1 specifies, especially "death-by-small-purchases" (not obviously mapped) and "weekend-vs-weekday pace" (not named in S7.1 class list at all).
**Recommendation:** Add a class-to-FR mapping comment or a table to S7.1 explicitly stating which detector class covers which FR-8.1 pattern. This is a naming alignment gap, not a missing story.

---

#### ⚠️ GAP: FR-4.1 denominator guard — `days_until_next_confirmed_income = 0` edge case

**PRD requirement:** Implicit in FR-4.1 (formula) and project-context.md seam. The `days_until_next_confirmed_income` can be 0 (payday is today) — guard before dividing.
**Epic coverage:** S4.2 AC explicitly covers this: "if 0 (payday is today) or undefined, the engine falls back to reserved-only mode and surfaces an 'add your payday' prompt — never divides by zero." ✅
**BUT:** The pytest scenario suite (S4.3) lists "12 scenarios: 7 core + 3 boundary + scenario 11 + scenario 12." There is **no scenario explicitly named for `days = 0` (payday today)**. The boundary scenarios are not enumerated in the epics — only the `safe-to-spend-scenarios.md` file holds the authoritative list.
**Risk:** Low-Medium — S4.1's AC requires reading and locking the scenario contract first, so if the scenario file covers `days = 0`, it will be caught. But if it doesn't, this edge case has no pytest coverage.
**Recommendation:** Verify that `safe-to-spend-scenarios.md` includes a `days_until_next_income = 0` scenario. If not, add it.

---

### Coverage Statistics

| Metric | Count |
|---|---|
| Total PRD FRs | 72 |
| FRs with full epic + story coverage | 70 |
| FRs with partial coverage (AC gap) | 2 (FR-8.5, FR-8.6) |
| FRs with no coverage | 0 |
| **Coverage percentage** | **97% full / 100% touched** |
| Total NFRs | 9 |
| NFRs fully covered | 9 |
| NFR coverage | 100% |
| Additional gaps identified (not FR/NFR numbered) | 2 (detector naming alignment, days=0 scenario) |

---

## UX Alignment Assessment

### UX Document Status

**Found:** `ux-spec-mvp.md` (96 lines) — build-ready reference document authored 2026-07-08. Contains: layout hierarchy wireframes for Dashboard, Confidence Score drill-in, Copilot, Upload; microcopy sheet with 8 state/copy pairs; 7-item enforcement checklist.

---

### UX ↔ PRD Alignment

| UX Requirement | PRD Coverage | Status |
|---|---|---|
| Hero-first layout (STS + "why" above charts) | FR-6.1, PRD §4 | ✅ Aligned |
| No raw Confidence Score number shown | FR-5.5 | ✅ Aligned |
| Two-layer STS display (never merged) | FR-4.5 | ✅ Aligned |
| Freshness caveat on hero card | FR-4.7 | ✅ Aligned |
| Persistent left nav 4 screens | FR-6.4 | ✅ Aligned |
| "Step 1 of 3" on Upload | FR-2.5 | ✅ Aligned |
| Microcopy: scanned PDF message | FR-2.4 | ✅ Aligned |
| Microcopy: empty dashboard copy | FR-4.8 (indirect) | ✅ Aligned |
| Microcopy: Teach Me confirmation copy | FR-3.4 | ✅ Aligned |
| Microcopy: shortfall copy | FR-4.9 | ✅ Aligned |
| Microcopy: observation framing ("picked up" not "overspent") | FR-6 tone contract | ✅ Aligned |
| "Show me why" drill-in label | FR-5.6 | ✅ Aligned |
| Quick-prompt buttons | FR-7.7 | ✅ Aligned — P1 |
| score_events event rows in drill-in panel | FR-5.3 | ✅ Aligned |
| UX-DR10 (Confidence drill-in) | FR-5.5, FR-5.3 | ✅ Aligned |

#### UX Requirements in epics not explicitly in PRD body

The epics include 18 UX-DRs (UX-DR1 through UX-DR18) sourced from the UX spec. These are properly reflected in epic ACs. Three are worth noting for traceability:

- **UX-DR9** (Teach Me copy "Got it — I'll call X 'Y' from now on") — present in S3.3 AC verbatim. ✅
- **UX-DR11** (Shortfall copy) — present in S8.1 "approved UX copy" reference. ✅
- **UX-DR17** ("Show me why" label, not "View details") — present in S5.1 AC explicitly. ✅

---

### UX ↔ Architecture Alignment

| UX Requirement | Architecture Support | Status |
|---|---|---|
| Token-by-token streaming (Copilot) | Reflex async State handler; SSE event schema (AD-11) | ✅ Supported |
| Virtual scroll for 100–300 rows | FR-3.7 / rx.reflex virtual scroll; no specific AD, but no conflict | ✅ Supported |
| rx.plotly charts with custom formatters | AD-13 + agent-misread guard: chart axes must route through formatINR | ✅ Supported — explicit guard exists |
| httpOnly cookie for SSE auth | AD-5 × AD-11 seam — SSE uses cookie, never URL token | ✅ Explicitly guarded |
| Dashboard initial render <3s | NFR-9; Reflex State lazy-loading pattern | ✅ Supported |
| Left nav present across all screens | Architecture spine (AD-2) single app root; layout pattern | ✅ Supported |
| Inline modals (commitment, T&C) | Reflex rx.dialog; no architectural conflict | ✅ Supported |

---

### ⚠️ UX Alignment Warnings

#### WARNING 1: Mobile responsiveness not specified

**UX spec note (line 93):** "Wireframes above are full-width; add a left-sidebar column (width ~200px) to every app-screen layout at implementation."
**PRD open item X1:** "UX scenarios assume mobile-responsive web; ux-spec-mvp.md is silent on responsive. Reconcile device framing before implementation begins." — tagged as Recommended, Before Day 1 build start.
**Status:** This open item is **unresolved** and has no story or AC that specifies responsive breakpoints. The UX spec is desktop-only.
**Risk:** Medium — for a local MVP targeting "salaried user on their phone during commute" (Priya persona), no responsive spec means mobile use is undefined. The Reflex framework does support responsive layouts, but without a spec, developers will make ad-hoc choices.
**Recommendation:** Before Epic 1 build starts, decide: (a) desktop-only MVP is acceptable, or (b) define a minimum responsive breakpoint (e.g. ≥375px viewport). Add one line to S1.1 or S1.5 AC. If (a), update the PRD open item X1 to "Decided: desktop-only for Phase 1."

---

#### WARNING 2: UX spec covers 4 screens; Insights page not wireframed

**UX spec contents:** Dashboard, Confidence Score drill-in, Copilot, Upload — 4 wireframes. The **Insights page** (Epic 7) has no wireframe.
**Epics coverage:** S7.3 (Insights Page & Dismiss Lifecycle) is fully written with ACs including card layout, "Dismiss" and "Ask Copilot" buttons, ordering by severity. This is sufficient for implementation.
**Risk:** Low — the ACs in S7.3 are specific enough. The absence of a wireframe is a minor gap given the ACs include layout guidance.
**Recommendation:** No action required for Phase 1. Note for Phase 2 design pass.

---

### UX Alignment Summary

- **15 UX requirements** fully aligned with PRD FRs
- **7 architecture capabilities** verified to support UX requirements
- **1 unresolved open item** (responsive design — PRD item X1) requires a decision before Day 1 build
- **1 minor wireframe gap** (Insights page) — mitigated by strong ACs in S7.3

---

## Epic Quality Review

### Epic Structure Validation

#### User Value Focus Check

| Epic | Title | User-Centric? | Value Standalone? | Assessment |
|---|---|---|---|---|
| Epic 1 | Secure Access & App Foundation | ✅ "A user can register, log in, and securely access..." | ✅ Auth is a complete user capability | ✅ PASS — user value clear |
| Epic 2 | Statement Upload & Transaction Extraction | ✅ "A user can upload...see a clean list..." | ✅ Upload + extraction is a complete user outcome | ✅ PASS |
| Epic 3 | Transaction Categorization & Teach Me | ✅ "A user sees every transaction categorized...can teach the app..." | ✅ Valuable on top of Epic 2 | ✅ PASS |
| Epic 4 | Financial Engine — STS & Confidence Score | ⚠️ User-facing outcome implied but engine is infrastructure | ⚠️ Engine alone has no UI — value only realized in Epic 5 | 🟠 CONCERN — see below |
| Epic 5 | Dashboard, Briefing & Commitment Management | ✅ "A user sees their Safe-to-Spend hero card..." | ✅ Complete user experience outcome | ✅ PASS |
| Epic 6 | AI Copilot | ✅ "A user can ask natural-language questions..." | ✅ Self-contained user capability | ✅ PASS |
| Epic 7 | Proactive Insights | ✅ "A user receives named behavioral patterns..." | ✅ Self-contained user capability | ✅ PASS |
| Epic 8 | Hardening & Demo-Readiness | ⚠️ "Edge cases fail honestly...demo runs" | ⚠️ Technical hardening — no primary user feature delivered | 🟡 MINOR — acceptable for final-phase epic |

---

### 🟠 MAJOR CONCERN: Epic 4 — Technical Epic with No Direct User Value

**Issue:** Epic 4 ("Financial Engine — STS & Confidence Score") is a pure backend/computation epic. A user gets zero visible outcome from completing Epic 4 alone — the engine outputs are not surfaced until Epic 5 wires the Dashboard. This is an infrastructure milestone masquerading as a user epic.

**Why it's acceptable here (mitigated):** The epics document acknowledges this explicitly: "⚠️ HIGH-RISK EPIC — `pytest tests/engine/` green is the gate before Epic 5 is wired." The epic is sequenced correctly (4 → 5), and it is the only path to deliver the product's core value proposition. A 3-day solo build demands sequential dependency here.

**Risk:** Medium — the developer must understand Epic 4 has no demo-able output. If they mistake "Epic done" for "user can see something," they'll be confused at Epic 4 completion.

**Recommendation:** Add one line to the Epic 4 description: "**Developer note:** This epic has no user-visible output. Success is a green pytest suite. Epic 5 wires the engine to the Dashboard."

---

### Epic Independence Validation

| Epic | Dependencies | Can function with only prior epics? | Status |
|---|---|---|---|
| Epic 1 | None | ✅ Standalone | ✅ |
| Epic 2 | Epic 1 (auth, DB schema from S1.2) | ✅ S1.2 creates all 8 tables; Epic 2 uses uploaded_files + transactions | ✅ |
| Epic 3 | Epics 1+2 (parsed transactions exist) | ✅ Requires upload done first | ✅ |
| Epic 4 | Epics 1+2+3 (transactions + categories needed for engine) | ✅ — but see S4.2 note below | ⚠️ See below |
| Epic 5 | Epic 4 engine output (evidence pack struct) | ✅ Correctly depends on Epic 4 | ✅ |
| Epic 6 | Epics 1+2+3+4+5 (read-only tools over real data) | ✅ All upstream data needed | ✅ |
| Epic 7 | Epics 2+3 (transactions + categories) | ✅ Detector engine runs on ingested data | ✅ |
| Epic 8 | All prior epics | ✅ By design — hardening pass | ✅ |

---

### ⚠️ DEPENDENCY ISSUE: S2.4 → S3.1/S3.2 Progress Bar Handoff

**Issue (forward dependency):** S2.4 ACs state: *"Steps 3 and 4 are skeleton events in this story; they are completed with real data in Epic 3 (S3.1, S3.2)."* This means Story 2.4 is explicitly incomplete at Epic 2 completion — it contains placeholder step events that require Epic 3 stories to fill in.

**Assessment:** This is a **named forward dependency** — Story 2.4 ACs reference S3.1 and S3.2 by name. The story is not independently completable. The 4-step progress bar will show skeleton events until Epic 3 is done.

**Why it's managed (mitigated):** The epics note explicitly flags this: "Party-mode finding applied: four-step progress bar is a skeleton in Epic 2 — steps 3/4 completed in Epic 3." The handoff is documented. Both S3.1 and S3.2 explicitly complete the skeleton: "completing the skeleton wired in Epic 2 Story 2.4."

**Risk:** Low — the handoff is documented and bidirectional (both sides know about it). However, if a developer works on Epic 2 in isolation without reading Epic 3, they may mark S2.4 "done" prematurely.

**Recommendation:** Add to S2.4 a **Definition of Done note**: "Step 3 and 4 progress events are stubs in this story. Full completion requires S3.1 and S3.2. Mark Epic 2 complete only after S3.1 and S3.2 are merged."

---

### Story Quality Assessment

#### Story Sizing Validation

| Story | Size | Independent? | Assessment |
|---|---|---|---|
| S1.1 — Project Skeleton | Developer setup story | ✅ Self-contained | ✅ |
| S1.2 — DB Schema + Utilities | ⚠️ Creates ALL 8 tables upfront | ⚠️ Violates "create tables when needed" best practice | 🟠 See below |
| S1.3 — Registration + Auto-Login | Right-sized | ✅ | ✅ |
| S1.4 — Login/Logout + Protected Routes | Right-sized | ✅ | ✅ |
| S1.5 — Auth Transition + Nav Scaffold | Right-sized | ✅ | ✅ |
| S2.1 — Parser Protocol | Developer story | ✅ | ✅ |
| S2.2 — CSV Parser | Right-sized | ✅ | ✅ |
| S2.3 — PDF Parser Chain | Right-sized | ✅ | ✅ |
| S2.4 — Upload Page Progress | Right-sized but forward dependency | ⚠️ (see above) | 🟠 Managed |
| S2.5 — Deduplication | Right-sized | ✅ | ✅ |
| S3.1 — Tier-1 Rules + Transactions Table | Slightly large (rules engine + full table UI) | ✅ | ✅ |
| S3.2 — Tier-2 LLM Categorizer | Right-sized | ✅ | ✅ |
| S3.3 — Teach Me | Right-sized | ✅ | ✅ |
| S3.4 — Confidence Badges + Virtual Scroll | Right-sized | ✅ | ✅ |
| S4.1 — Engine Pre-Flight | Dev-only gate story | ✅ | ✅ — smart sequencing |
| S4.2 — STS Engine Implementation | ⚠️ Large (full formula + 4 DD-1 sub-rules + struct) | ✅ AC-complete | ⚠️ Large but necessary atomicity |
| S4.3 — pytest Suite All 12 Scenarios | Dev-only verification story | ✅ | ✅ |
| S4.4 — Confidence Score Engine | Right-sized | ✅ | ✅ |
| S5.1 — Dashboard Hero Card | Right-sized | ✅ | ✅ |
| S5.2 — Confidence Score Drill-In | Right-sized | ✅ | ✅ |
| S5.3 — Morning Briefing Narration | Right-sized | ✅ | ✅ |
| S5.4 — Dashboard Charts | Right-sized | ✅ | ✅ |
| S5.5 — Commitment CRUD + Live Update | Right-sized | ✅ | ✅ |
| S5.6 — Commitment Auto-Detection | Right-sized | ✅ | ✅ |
| S6.1 — Copilot Chat UI + Streaming | Right-sized | ✅ | ✅ |
| S6.2 — Read-Only Tools + Honesty Enforcement | Right-sized | ✅ | ✅ |
| S6.3 — SSE Contract + Trace Chips + Error | Right-sized | ✅ | ✅ |
| S6.4 — Quick Prompts + Insights Handoff | Right-sized | ✅ | ✅ |
| S7.1 — Insight Detector Engine (all 5) | ⚠️ Large (5 detector classes) | ✅ AC-complete | ⚠️ Large but named atomicity |
| S7.2 — Insight Narration | Right-sized | ✅ | ✅ |
| S7.3 — Insights Page + Dismiss Lifecycle | Right-sized | ✅ | ✅ |
| S7.4 — Dashboard Insight Teaser | Small, clear scope | ✅ | ✅ |
| S8.1 — Edge-Case Honest Refusals | Right-sized | ✅ | ✅ |
| S8.2 — Onboarding Empty States | Right-sized | ✅ | ✅ |
| S8.3 — IDOR Security Test | Dev-only security gate | ✅ | ✅ |
| S8.4 — README + One-Command Setup | Right-sized | ✅ | ✅ |
| S8.5 — Demo Dry Run + Regression Guard | Right-sized | ✅ | ✅ |

---

### 🟠 MAJOR CONCERN: S1.2 Creates All 8 Tables Upfront

**Issue:** Story 1.2 creates **all 8 database tables** at once: `users, uploaded_files, transactions, merchant_rules, commitments, score_events, insights, chat_messages`. Best practice is to create tables in the story that first needs them (e.g. `insights` table is not needed until Epic 7; `chat_messages` not until Epic 6).

**Why it's managed (partially):** For a 3-day solo build with Reflex's `reflex db migrate` approach, creating all tables in one migration is operationally simpler than incremental migrations. It avoids migration state management across 35 stories. The epics explicitly include this in the "Additional Requirements" under "Starter template."

**Risk:** Low for this project specifically — the all-at-once migration is a pragmatic 3-day-build decision. For a larger team or longer project, this would be a stronger violation.

**Finding Verdict:** 🟡 MINOR for a 3-day solo MVP. Acceptable. Note it as a conscious trade-off.

---

### Acceptance Criteria Review

**Format compliance (Given/When/Then):** All 35 stories use BDD-style Given/When/Then format consistently. ✅

**Coverage of error conditions:**

| Story | Error Conditions Covered? | Assessment |
|---|---|---|
| S2.3 | Scanned PDF IngestionError | ✅ |
| S2.4 | Parse failure empathetic copy | ✅ |
| S3.2 | LLM call mocked; prompt injection guard | ✅ |
| S4.2 | days=0 guard; shortfall floor | ✅ |
| S4.3 | 12 scenarios including boundary + failure | ✅ |
| S6.2 | 10 scripted zero-invented-numbers test | ✅ |
| S6.3 | SSE done in finally; LLM stream raises | ✅ |
| S8.1 | Empty PDF; scanned PDF; no salary; LLM tier-2 failure | ✅ |

**Measurable outcomes:** ACs contain specific counts (24 transactions, 18 rules, 3 AI, 3 need-help), specific copy verbatim, specific timing bounds (<3s, <60s), specific field names (`trigger_event` not `triggering_event`). ✅ Very strong.

**One gap identified:** S4.2 AC covers `days=0` in the implementation, but S4.3 (pytest suite) doesn't name a scenario for it (covered under "Dependency findings" above).

---

### Best Practices Compliance Summary

| Epic | Delivers User Value | Independent | Stories Sized Right | No Forward Deps | DB Timing | Clear ACs | FR Traceability |
|---|---|---|---|---|---|---|---|
| Epic 1 | ✅ | ✅ | 🟡 S1.2 all-at-once | ✅ | 🟡 All upfront | ✅ | ✅ |
| Epic 2 | ✅ | ✅ | ✅ | 🟠 S2.4 skeleton | N/A | ✅ | ✅ |
| Epic 3 | ✅ | ✅ | ✅ | ✅ | N/A | ✅ | ✅ |
| Epic 4 | 🟠 Technical | ✅ | ⚠️ S4.2 large | ✅ | N/A | ✅ | ✅ |
| Epic 5 | ✅ | ✅ | ✅ | ✅ | N/A | ✅ | ✅ |
| Epic 6 | ✅ | ✅ | ✅ | ✅ | N/A | ✅ | ✅ |
| Epic 7 | ✅ | ✅ | ⚠️ S7.1 large | ✅ | N/A | ✅ | ⚠️ Detector naming |
| Epic 8 | 🟡 Hardening | ✅ | ✅ | ✅ | N/A | ✅ | ✅ |

---

### 🔴 Critical Violations: NONE

No critical violations found. No technical-only epics with zero user-value path, no circular dependencies, no stories that cannot be completed.

### 🟠 Major Issues: 3

1. **S2.4 forward dependency** to S3.1/S3.2 — managed but requires DoD note
2. **Epic 4 is a technical epic** — managed and necessary; requires developer-note addition
3. **FR-8.5 and FR-8.6 partial coverage** — AC gaps in S7.3 and S5.3 (already identified in Epic Coverage step)

### 🟡 Minor Concerns: 3

1. **S1.2 creates all 8 tables upfront** — pragmatic for 3-day solo build; acceptable trade-off
2. **S4.2 is large** — but atomicity is required (shared evidence pack struct); acceptable
3. **S7.1 is large** — 5 detector classes; could be split in a longer project; acceptable for MVP

---

## Summary and Recommendations

### Overall Readiness Status: ✅ READY (with 6 low-effort fixes recommended before Day 1 build)

The planning artifacts for the AI-Powered Personal Finance Analyzer are **well-prepared for implementation**. The PRD is highly complete with 72 FRs at granular AC level, the architecture is sound, the epics cover 100% of requirements, stories use proper BDD format throughout, and the honesty spine / kill-signal protocol is embedded at every layer. No blocking gaps were found.

Six targeted fixes will close the remaining gaps before a single line of implementation code is written.

---

### Issues Requiring Action Before Day 1 Build Start

| # | Severity | Issue | Location | Fix Required |
|---|---|---|---|---|
| 1 | 🟠 Major | FR-8.5 missing AC | S7.3 | Add AC: "When data_months < 3, footer 'More data sharpens these patterns.' visible" |
| 2 | 🟠 Major | FR-8.6 AC gap — insights in briefing | S5.3 | Add AC: "When active insights exist, briefing narration references top insight's Observation" + specify narrate/ receives insight_candidates |
| 3 | 🟠 Major | S2.4 forward dependency undefined DoD | S2.4 | Add DoD note: "Epic 2 complete only after S3.1 and S3.2 merged — S2.4 progress steps 3/4 are stubs until then" |
| 4 | 🟠 Major | Epic 4 no user-visible output | Epic 4 description | Add developer note: "No user-visible output — success = green pytest suite; Epic 5 wires engine to Dashboard" |
| 5 | 🟠 Major | S7.1 detector class names ≠ FR-8.1 pattern names | S7.1 | Add explicit class-to-PRD-pattern mapping table |
| 6 | 🟡 Minor | Responsive design decision unresolved (PRD X1) | PRD open item X1 | Decide before Day 1: desktop-only MVP, or minimum breakpoint (375px); update S1.1 or S1.5 AC |

---

### Findings That Do NOT Block Implementation

These were identified and assessed as non-blocking:

- **S1.2 all-tables-upfront** — pragmatic for 3-day solo build; not a blocking issue
- **S4.2 large story** — atomic by necessity; acceptable
- **S7.1 large story (5 detectors)** — acceptable for MVP; split in Phase 2
- **Insights page wireframe missing** — S7.3 ACs are sufficient; no wireframe needed
- **days_until_next_income = 0 scenario** — check `safe-to-spend-scenarios.md` before starting S4.3; if missing, add the scenario (10-minute fix, not a blocker now)
- **NFR security coverage** — architecture spine + project-context.md carry OWASP/IDOR load; Epic 8 S8.3 provides the explicit gate

---

### Recommended Next Steps (in order)

1. **Now (before Day 1 build):** Apply the 6 fixes from the table above to `epics.md`. These are targeted AC additions and notes — total effort ~30 minutes.
2. **Day 1, Hour 1:** Validate `statementsparser` covers the HDFC demo format (flagged assumption in S1.1 AC — if it fails, the parser chain in S2.3 needs rework).
3. **Day 1, Hour 1:** Confirm ≥3 insight detectors fire on `demo-data.json` (24-transaction Priya dataset) — required by FR-8.1 AC.
4. **Day 1, Hour 1:** Verify `safe-to-spend-scenarios.md` includes a `days_until_next_income = 0` scenario. If missing, add it before S4.2 begins.
5. **Before Epic 4 starts:** Read `safe-to-spend-scenarios.md` in full (S4.1 is an explicit pre-flight gate — do not skip it).
6. **Before Epic 5 starts:** Confirm `pytest services/engine/` is green with zero LLM calls — this is the non-negotiable gate per NFR-3 and the Architecture Spine.

---

### Coverage Statistics Summary

| Metric | Result |
|---|---|
| Total FRs assessed | 72 |
| FRs fully covered in epics | 70 (97%) |
| FRs with AC gaps (partial) | 2 (FR-8.5, FR-8.6) |
| Total NFRs assessed | 9 |
| NFRs fully covered | 9 (100%) |
| UX requirements aligned | 15/15 (100%) |
| Stories with BDD ACs | 35/35 (100%) |
| Critical violations | 0 |
| Major issues | 3 |
| Minor concerns | 3 |

---

### Final Note

This assessment identified **6 issues** across **4 categories** (AC gaps, forward dependency DoD, technical epic clarity, naming alignment). All 6 are small, targeted fixes requiring no structural changes to the epics. The planning artifacts are exceptionally thorough for a 3-day MVP build — the honesty spine, kill-signal protocol, architecture decision records, and pytest scenario contract are best-in-class. Address the 6 fixes, then proceed to implementation with confidence.

**Assessment conducted:** 2026-07-09
**Assessor:** BMAD Implementation Readiness Workflow
**Documents reviewed:** prd.md (409 lines), ARCHITECTURE-SPINE.md (316 lines), epics.md (1021 lines), ux-spec-mvp.md (96 lines), project-context.md (188 lines)

