# Design Log

**Project:** AI-Powered-Personal-Finance-Analyzer
**Started:** 2026-07-07
**Method:** Whiteport Design Studio (WDS)

---

## Backlog

> Business-value items. Add links to detail files if needed.

- [x] Complete product brief — Phase 1
- [x] Define trigger map — Phase 2 (Dream mode; personas Rohan & Kavya pending user confirmation)
- [x] Create user scenarios — Phase 3 (3 scenarios, 8 pages; all Priya-focused per MVP scope)
- [ ] Resolve open Safe-to-Spend design questions (data-latency handling, Confidence Score cold-start, multi-bank gap) — carried from `problem-solution-2026-07-07.md`
- [ ] Legal opinion on FIU registration / SEBI Investment Adviser boundary before scaling past 10,000 users
- [ ] Category-specific (not general fintech) TAM/SAM/SOM sizing pass
- [ ] AA consent-screen plain-language redesign

---

## Current

| Task | Started | Agent |
|------|---------|-------|
| — | — | — |

**Rules:** Mark what you start. Complete it when done (move to Log). One task at a time per agent.

---

## Design Loop Status

> Per-page design progress. Updated by agents at every design transition.

| Scenario | Step | Page | Status | Updated |
|----------|------|------|--------|---------|
| 01-priyas-first-honest-morning | 01.1 | Register | specified | 2026-07-08 |
| 01-priyas-first-honest-morning | 01.2 | Login (auto-authentication) | specified | 2026-07-08 |
| 01-priyas-first-honest-morning | 01.3 | Statement Upload | specified | 2026-07-08 |
| 01-priyas-first-honest-morning | 01.4 | Transactions Table | specified | 2026-07-08 |
| 01-priyas-first-honest-morning | 01.5 | Dashboard | specified | 2026-07-08 |
| 01-priyas-first-honest-morning | 01.6 | AI Insights & Recommendations | specified | 2026-07-08 |
| 01-priyas-first-honest-morning | 01.7 | Copilot Chat | specified | 2026-07-08 |
| 02-priya-protects-what-matters | 02.1 | Commitments Management | specified | 2026-07-08 |
| 03-priyas-two-tap-gut-check | 03.1 | Copilot Chat (return-visit) | specified | 2026-07-08 |

**Status values:** `discussed` → `wireframed` → `specified` → `explored` → `building` → `built` → `approved` | `removed`

---

## Progress

### 2026-07-07 - Phase 1: Product Brief Complete

**Agent:** Saga (Product Brief)
**Brief Level:** Complete (synthesized directly from prior sessions at user's request, to compress a 30-60 min interactive flow into a single fast-turnaround draft)

**Artifacts Created:**
- `A-Product-Brief/project-brief.md`

**Source artifacts synthesized (all pre-existing, read in full before drafting):**
- `brainstorming/brainstorm-ai-powered-personal-finance-analyzer-2026-07-06/brainstorm-intent.md`
- `design-thinking-2026-07-07.md`
- `innovation-strategy-2026-07-07.md`
- `problem-solution-2026-07-07.md`
- `planning-artifacts/research/domain-ai-driven-personal-finance-management-apps-india-research-2026-07-07.md`
- `planning-artifacts/research/market-personal-finance-copilot-market-india-research-2026-07-07.md`

**Summary:** Established the strategic foundation for the AI Financial Copilot — an empathetic, proactive personal finance app for financially-anxious salaried Indian adults ("Priya" persona), centered on a daily Safe-to-Spend briefing and a Financial Confidence Score, with honesty-under-uncertainty as the core competitive moat. The brief corrects several claims from earlier sessions per independent research (Walnut→axio, Jupiter/Fi as closer competitors than assumed, Cleo's agentic AI narrowing the 18-month founding window, D30 retention and freemium-conversion targets re-scoped against real category benchmarks) and hardens regulatory constraints (SEBI Investment Adviser boundary, DPDP Rule 4 timing, AA adoption gap of only 38% of borrowers) as load-bearing product requirements rather than footnotes.

**Next:** Phase 2 - Trigger Mapping

---

### 2026-07-07 - Phase 2: Trigger Mapping Complete (Dream mode)

**Agent:** Saga (Trigger Mapping)
**Mode:** Dream (autonomous generation + self-review; user selected [D])

**Artifacts Created (in `B-Trigger-Map/`):**
- `trigger-map.md` — hub with Mermaid diagram + navigation
- `01-business-goals.md` — vision + SMART objectives (3 priority tiers)
- `personas/02-priya-the-overwhelmed-earner.md` — PRIMARY (THE ENGINE)
- `personas/03-rohan-the-money-managing-partner.md` — SECONDARY
- `personas/04-kavya-the-wellness-sponsor.md` — TERTIARY (Year-2 B2B2C)
- `05-key-insights.md` — design implications + focus statement
- `feature-impact-analysis.md` — persona-weighted feature prioritization
- `handover-to-ux.md` — Phase 2 → Phase 3 handover package (wrap)
- Session log: `_progress/agent-experiences/2026-07-07-trigger-map-D.md`

**Summary:** Mapped the business goals to user psychology using the Effect Mapping form. Priya (primary) drives the flywheel: a measurably calmer user → advocate → growth → ecosystem. Vision = "become the most trusted daily financial voice for anxious salaried Indians." The two highest-scoring features (perfect 11/11) are the honesty layer and trust-first onboarding — the moat, made explicit. Rohan (household/Premium multiplier) and Kavya (Year-2 employer-sponsor distribution multiplier) are analyst-inferred extensions of the brief's secondary-user notes, deliberately kept from diluting Priya's Phase-1 focus.

**⚠️ Pending user confirmation:** Because Dream mode generates autonomously, the personas Rohan and Kavya, and the prioritization, have **not been user-confirmed**. Recommended next action: review these two personas, then proceed to Phase 3.

**Next:** Phase 3 - UX Scenarios

---

### 2026-07-08 — Phase 3: UX Scenarios Complete

**Agent:** Claude Code (UX Scenario Facilitator — the `wds-3-scenarios` skill declares no named persona)
**Scenarios:** 3 scenarios covering 8 unique pages (Suggest mode for the 8-question dialogs)
**Quality:** Excellent (all 3 scenarios: Completeness 7/7, Quality 7/7, Mistakes-Avoided 7/7, Best-Practices 4/4)

**Artifacts Created:**
- `C-UX-Scenarios/00-ux-scenarios.md` — Scenario index + coverage matrix
- `C-UX-Scenarios/01-priyas-first-honest-morning/01-priyas-first-honest-morning.md` — Scenario 01 outline
- `C-UX-Scenarios/01-priyas-first-honest-morning/01.1-register/01.1-register.md`
- `C-UX-Scenarios/01-priyas-first-honest-morning/01.2-statement-upload/01.2-statement-upload.md`
- `C-UX-Scenarios/01-priyas-first-honest-morning/01.3-transactions-table/01.3-transactions-table.md`
- `C-UX-Scenarios/01-priyas-first-honest-morning/01.4-dashboard/01.4-dashboard.md`
- `C-UX-Scenarios/01-priyas-first-honest-morning/01.5-ai-insights-recommendations/01.5-ai-insights-recommendations.md`
- `C-UX-Scenarios/01-priyas-first-honest-morning/01.6-copilot-chat/01.6-copilot-chat.md`
- `C-UX-Scenarios/02-priya-protects-what-matters/02-priya-protects-what-matters.md` — Scenario 02 outline
- `C-UX-Scenarios/02-priya-protects-what-matters/02.1-login/02.1-login.md`
- `C-UX-Scenarios/02-priya-protects-what-matters/02.2-commitments-management/02.2-commitments-management.md`
- `C-UX-Scenarios/03-priyas-two-tap-gut-check/03-priyas-two-tap-gut-check.md` — Scenario 03 outline
- `C-UX-Scenarios/03-priyas-two-tap-gut-check/03.1-copilot-chat/03.1-copilot-chat.md`

**Summary:** Created 3 linear-sunshine-path scenarios, all anchored to Priya (the MVP's 8-page surface has no Rohan/Kavya features). Scenario 01 (Priya's First Honest Morning) is the full golden path — Register → Statement Upload → Transactions Table → Dashboard → AI Insights → Copilot Chat — serving the PRIMARY anxiety-reduction goal; Scenario 02 (Priya Protects What Matters) covers Login → Commitments Management for the ring-fencing/preparedness goal; Scenario 03 (Priya's Two-Tap Gut-Check) is a repurposed habitual return-visit to the Copilot for the growth/habit goal. Two page-inventory decisions shaped the pass: the **Confidence Score Drill-in was removed from scope** at Step 2, and the plan was **revised mid-outlining** to match the app's real navigation backbone (registration auto-logs in; AI Insights promoted to its own page; Login moved to Scenario 02). Page source was `prd.md`/`epics-and-stories.md`/`ux-spec-mvp.md`, not the Product Brief (which describes the Phase-2 WhatsApp channel, not the Phase-1 web surface). Copilot Chat is intentionally documented as two distinct user moments across Scenarios 01 and 03.

**Next:** Phase 4 — UX Design

---

### 2026-07-08 — Phase 4: UX Design — Scenario 01 Complete (Dream Mode)

**Agent:** Freya (Claude Code, WDS Phase 4 UX Designer)
**Mode:** Dream (autonomous generation + user review)
**Scenario:** 01 — Priya's First Honest Morning (P1, golden path)
**Pages:** 7 / 7 specified *(originally 6; Login added as 01.2 in post-generation restructure — see Step 19)*

**Artifacts Created:**
- `C-UX-Scenarios/01-priyas-first-honest-morning/01.1-register/01.1-register.md`
- `C-UX-Scenarios/01-priyas-first-honest-morning/01.2-login/01.2-login.md` *(added in restructure)*
- `C-UX-Scenarios/01-priyas-first-honest-morning/01.3-statement-upload/01.3-statement-upload.md`
- `C-UX-Scenarios/01-priyas-first-honest-morning/01.4-transactions-table/01.4-transactions-table.md`
- `C-UX-Scenarios/01-priyas-first-honest-morning/01.5-dashboard/01.5-dashboard.md`
- `C-UX-Scenarios/01-priyas-first-honest-morning/01.6-ai-insights-recommendations/01.6-ai-insights-recommendations.md`
- `C-UX-Scenarios/01-priyas-first-honest-morning/01.7-copilot-chat/01.7-copilot-chat.md`

**Summary:** Specified all 6 pages of the golden path in Dream mode. Each page spec follows the WDS template: Page Metadata, Overview, Layout Structure, Spacing, Typography, Page Sections (with Object IDs), Page States, Validation/API/Accessibility, Technical Notes, and Open Questions. Key design decisions across the scenario: (1) The honesty layer is explicitly designed into every touchpoint — freshness caveats on the Dashboard hero, step-by-step transparent parse progress on Upload, `?`/`AI` confidence badges on Transactions, the "Why?" expander on the hero card, exact-data evidence blocks on Insights, and data-trace chips on every Copilot response. (2) The Confidence Score is never surfaced as a raw number — only as a named chip (High/Medium/Low) with a contextual tooltip. (3) Copilot Chat (01.6) is documented as the shared UI for both Scenario 01 (first-touch exploratory) and Scenario 03 (habitual gut-check); the 03.1 spec will document state differences only. (4) The "information not advice" SEBI boundary is enforced at the design layer, not just the prompt layer — action suggestions are framed as "consider" not "do."

**Next:** User review of Scenario 01 specs → Scenario 02 (Priya Protects What Matters) or direct to agentic development

---

### 2026-07-08 — Phase 4: UX Design — Scenarios 02 & 03 Complete (Dream Mode)

**Agent:** Freya (Claude Code, WDS Phase 4 UX Designer)
**Mode:** Dream (autonomous generation + user review)
**Scenarios:** 02 — Priya Protects What Matters (2 pages) + 03 — Priya's Two-Tap Gut-Check (1 page)
**Pages:** 3 / 3 specified

**Artifacts Created:**
- `C-UX-Scenarios/02-priya-protects-what-matters/02.1-commitments-management/02.1-commitments-management.md` *(originally 02.2; renumbered in restructure — see Step 19)*
- `C-UX-Scenarios/03-priyas-two-tap-gut-check/03.1-copilot-chat/03.1-copilot-chat.md`

> **Note:** The Login page originally generated as 02.1 was moved to Scenario 01 as 01.2 (auto-authentication transition). See Step 19 for full restructure details.

**Summary:** Commitments Management (02.1, originally 02.2) is the "protection payoff" page — the Safe-to-Spend number updating in real-time as Priya adds a commitment is the designed key UX moment; every label uses "protect" not "save." Criticality selector has 3 levels (Critical/Important/Flexible) with default Important (conservative-by-default). Copilot Chat return-visit (03.1) is specified as a delta from 01.6 — only the differences are documented: gut-check quick-prompt bar, verdict badge (Yes/Stretch/No), brevity-constrained response mode, and decision-focused suggestion chips. The gut-check answer is constrained to ≤ 3 sentences server-side. Honesty constraints apply equally to unfavourable answers (No = factual limit, not a judgment).

**All 9 unique pages across 3 scenarios are now specified.**

**Next:** User review of all specs → Agentic development (Phase 5) or Design System extraction

---

### 2026-07-08 — Phase 4: Scenario Restructure — Login Moved from 02.1 to 01.2

**Agent:** Freya (Claude Code, WDS Phase 4 UX Designer)
**Requested by:** ALPHA
**Change:** Moved the Login page from Scenario 02 step 02.1 to Scenario 01 step 01.2 (between Register and Statement Upload), and completely rewrote its purpose.

**Rationale:** The Phase 3 Scenario 02 Login spec was a returning-user login page (email + password + biometric). The original Phase 3 design intent for Scenario 01 was that registration auto-authenticates — there was no explicit Login step. On post-generation review, ALPHA decided this auto-authentication moment should be an explicit, documented transition beat: a page that confirms account creation and sets the auth token before forwarding Priya to Statement Upload. This is a UX clarity decision: Priya deserves to see "Account created!" before being pushed into the next task.

**Files renamed (Scenario 01):**
- `01.2-statement-upload/` → `01.3-statement-upload/`
- `01.3-transactions-table/` → `01.4-transactions-table/`
- `01.4-dashboard/` → `01.5-dashboard/`
- `01.5-ai-insights-recommendations/` → `01.6-ai-insights-recommendations/`
- `01.6-copilot-chat/` → `01.7-copilot-chat/`

**Files moved/created (Scenario 02 → Scenario 01):**
- `02-priya-protects-what-matters/02.1-login/` → `01-priyas-first-honest-morning/01.2-login/` *(completely rewritten as auto-authentication transition)*
- `02-priya-protects-what-matters/02.2-commitments-management/` → `02-priya-protects-what-matters/02.1-commitments-management/` *(renumbered)*

**Nature of 01.2 Login rewrite:** The returning-user login (email/password form, biometric shortcut, forgot password) was replaced with an auto-authentication transition page — no form, no user action required, just a confirmation beat + progress indicator + auto-redirect to /upload. The returning-user /login page is explicitly noted as a separate, standalone page outside scenario numbering.

**All cross-references updated:** Nav links, scenario outlines, 00-ux-scenarios.md, Design Loop Status table, and internal body text across all 9 page specs.

---

## Key Decisions

| Date | Decision | Phase | By |
|------|----------|-------|-----|
| 2026-07-07 | Brief level: Complete — but produced as a single synthesized draft (not 36 sequential dialog steps) to meet a 15-minute turnaround constraint | Phase 1: Product Brief | Saga + ALPHA |
| 2026-07-07 | Corrected competitor list: axio (not Walnut); Jupiter/Fi treated as closer competitors than the original innovation-strategy doc assumed; Mint treated as defunct/historical only | Phase 1: Product Brief | Saga + ALPHA |
| 2026-07-07 | Pricing (₹199/₹499) and D30/conversion targets reframed as hypotheses to validate in Wizard-of-Oz testing, not settled planning figures | Phase 1: Product Brief | Saga + ALPHA |
| 2026-07-07 | Business model risk flagged: pure-subscription revenue has a global ~$100M ceiling pattern — revenue diversification must be explored before scaling spend | Phase 1: Product Brief | Saga + ALPHA |
| 2026-07-07 | Regulatory framing hardened: all product output must read as "information," never "advice," with a legal opinion required before the 10,000-user checkpoint | Phase 1: Product Brief | Saga + ALPHA |
| 2026-07-07 | Trigger Map run in Dream (autonomous) mode; three target groups defined — Priya (primary/engine), Rohan (secondary/household+Premium), Kavya (tertiary/Year-2 employer sponsor) | Phase 2: Trigger Mapping | Saga |
| 2026-07-07 | Honesty layer + trust-first onboarding scored highest (11/11) in feature impact — the moat is the priority, not a hero feature | Phase 2: Trigger Mapping | Saga |
| 2026-07-07 | Rohan & Kavya personas are analyst-inferred (not user-elicited) — flagged as pending user confirmation before Phase 3 | Phase 2: Trigger Mapping | Saga |
| 2026-07-08 | Confidence Score Drill-in page removed from Phase 3 scope (reduced inventory 8→7 at Step 2; later net 8 after adding AI Insights page) | Phase 3: Scenarios | Claude Code + ALPHA |
| 2026-07-08 | Scenario plan revised mid-outlining to the app's real nav backbone: registration auto-logs in (no separate login in Scenario 01); AI Insights & Recommendations promoted from inline Dashboard element to its own page; Login moved to Scenario 02 | Phase 3: Scenarios | Claude Code + ALPHA |
| 2026-07-08 | Scenario 03 repurposed from a duplicate first-touch Copilot scenario into a distinct habitual return-visit gut-check; Copilot Chat intentionally documented as two user moments (Scenarios 01 & 03) | Phase 3: Scenarios | Claude Code + ALPHA |
| 2026-07-08 | Page inventory sourced from `prd.md`/`epics-and-stories.md`/`ux-spec-mvp.md` (the Phase-1 web MVP surface), not the Product Brief (which describes the Phase-2 WhatsApp channel) | Phase 3: Scenarios | Claude Code + ALPHA |
| 2026-07-08 | 8-question scenario dialogs run in Suggest mode (facilitator drafts, user reviews) rather than step-by-step Conversation mode, given rich existing Trigger Map/PRD context | Phase 3: Scenarios | Claude Code + ALPHA |
| 2026-07-08 | Login moved from Scenario 02 step 02.1 to Scenario 01 step 01.2 — rewritten as auto-authentication transition (no form); returning-user /login is a separate standalone page; Scenario 02 now has 1 step (Commitments Management) | Phase 4: UX Design | Freya + ALPHA |

---

## About This Folder

- **This file** — Single source of truth for project progress
- **agent-experiences/** — Compressed insights from design discussions (dated files)
- **wds-project-outline.yaml** — Project configuration from Phase 0 setup (not yet run for this project)
