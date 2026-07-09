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
| 01-priyas-first-honest-morning | 01.1 | Register | built | 2026-07-08 |
| 01-priyas-first-honest-morning | 01.2 | Login (auto-authentication) | built | 2026-07-08 |
| 01-priyas-first-honest-morning | 01.3 | Statement Upload | built | 2026-07-08 |
| 01-priyas-first-honest-morning | 01.4 | Transactions Table | built | 2026-07-08 |
| 01-priyas-first-honest-morning | 01.5 | Dashboard | built | 2026-07-08 |
| 01-priyas-first-honest-morning | 01.6 | AI Insights & Recommendations | built | 2026-07-08 |
| 01-priyas-first-honest-morning | 01.7 | Copilot Chat | built | 2026-07-08 |
| 02-priya-protects-what-matters | 02.1 | Commitments Management | building | 2026-07-09 |
| 02-priya-protects-what-matters | 02.1 | Commitments Management | built | 2026-07-09 |

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

### 2026-07-08 — Phase 5: Prototyping — Scenario 01 Setup & Analysis

**Agent:** Claude Code (WDS Phase 5 Implementation Partner)
**Activity:** [P] Prototyping
**Scenario:** 01 — Priya's First Honest Morning (7 pages)

**Setup decisions (initiation dialog):**
- Device: Desktop + Mobile (Fully Responsive, 375→1920px)
- Fidelity: Generic Gray Model (wireframe) — no design system exists yet
- Language: English only (no switcher)
- Demo data: Priya dataset (HDFC June 2026 statement, ₹2,840 safe-to-spend, Medium confidence, 24 transactions incl. 3 needs-review, 3 EMIs) — internally consistent across all 7 pages

**Artifacts Created (in `prototypes/01-priyas-first-honest-morning-Prototype/`):**
- `PROTOTYPE-ROADMAP.md` — scenario overview + setup decisions + build sequence
- `data/demo-data.json` — Priya dataset (single source of truth)
- `work/Logical-View-Map.md` — 7 logical views (1:1 with steps), states, build order, honesty checklist
- Folder scaffold: `data/ work/ stories/ shared/ components/ pages/ assets/`

**Analysis result:** 7 distinct logical views, linear golden path, no view reuse within the scenario. Build order V1→V7 (01.1 Register → 01.7 Copilot Chat). V7 is the shared base for Scenario 03's return-visit variant (out of scope here).

**Next:** Step 3 — Logical View Breakdown (section-by-section) → build page-by-page starting with 01.1 Register

---

### 2026-07-08 — Phase 5: Prototyping — Scenario 01 Fully Built (all 7 views)

**Agent:** Claude Code (WDS Phase 5 Implementation Partner)
**Activity:** [P] Prototyping — section-by-section build (Step 1 strict for V1, fast mode for V2–V7 at user request)
**Result:** All 7 golden-path views built, self-verified, and integration-tested.

**Views built (in `prototypes/01-priyas-first-honest-morning-Prototype/`):**
- `01.1-register.html` — form + validation (7 rules) + auto-auth redirect
- `01.2-login.html` — auto-authentication transition (confirm + auto-advance + error fallback)
- `01.3-statement-upload.html` — transparent step-by-step parse (18 by rules · 3 by AI · 3 need help)
- `01.4-transactions-table.html` — 24 rows, filter chips, inline "Teach Me" correction with re-apply
- `01.5-dashboard.html` — Safe-to-Spend hero (₹2,840 / ₹8,200), Medium confidence chip + tooltip, "Why?" expander, donut, commitments, bottom nav
- `01.6-ai-insights-recommendations.html` — O→E→E→A insight cards with exact-data evidence, dismiss, Ask-Copilot handoff
- `01.7-copilot-chat.html` — simulated token streaming, data-trace chips, honesty contract, pre-populated context from Insights

**Shared infra:** `shared/styles.css` (Gray Model tokens + all component primitives), `format.js`, `data.js`, `nav.js`. Demo data: `data/demo-data.json` (internally consistent across all views).

**Verification:** Headless Chrome + DevTools Protocol. Per-view functional checks all pass (Register 18/18, Login+Upload 14/14, Transactions 12/12, Dashboard 18/18, Insights+Copilot 23/23); full golden-path integration test 7/7 with zero console errors. Two visual bugs found & fixed during verification (transaction meta stacking; Copilot input bar / bottom-nav overlap).

**Honesty layer realized in the UI:** freshness caveats, confidence-as-chip (never raw number), "Why?" reasoning from real data, transparent parse breakdown, exact-data evidence blocks, Copilot data-trace chips + explicit uncertainty ("one month of data → Medium"), observation-not-judgment tone, "information not advice" framing.

**Next:** User review of the running prototype → acceptance testing ([T]) or build Scenarios 02 & 03.

---

### 2026-07-08 — Phase 5: Prototyping — Scenario 01 Refinements & Wrap

**Agent:** Claude Code (WDS Phase 5 Implementation Partner)
**Activity:** [P] Prototyping — post-build iterative refinement (interactive review with ALPHA)

**Refinements applied (all verified via headless Chrome + CDP, zero console errors):**
1. **Branded visual theme** — upgraded from Gray Model to a calm **teal** fintech identity (color, elevation, pill buttons, designed donut palette). All theming driven from `shared/styles.css :root` tokens, so all 7 pages rethemed at once.
2. **Left navigation, persistent** across all 4 authenticated app screens (Transactions, Dashboard, Insights, Copilot) — mobile icon rail / desktop labeled sidebar. Register/Login/Upload remain nav-free.
3. **Transactions** — removed horizontal chip scroll (chips now wrap); redesigned top area; added a "See my Dashboard →" CTA in the header (left nav supersedes the old sticky action bar).
4. **Nav labels/order** — `Transactions · Dashboard · Insights · Copilot Chat`; "Home"→"Dashboard", "Commitments" slot → "Insights" (points to `01.6`), "Copilot"→"Copilot Chat".
5. **Dashboard "+ Add a commitment"** — now opens an inline **modal form** (name/amount/date/criticality) that adds to the timeline and **updates Safe-to-Spend live** (the Scenario-02 "protection payoff" moment, realized on the Dashboard).

**Wrap documents created (in `prototypes/01-priyas-first-honest-morning-Prototype/`):**
- `README.md` — run instructions, screen map, structure, honesty layer, scope
- `HANDOFF.md` — deltas from the specs + production API/data-contract notes for dev & acceptance testing
- `PROTOTYPE-ROADMAP.md` — updated (fidelity note, all 7 views ✅ Built)

**Open cosmetic gap:** Dashboard morning-briefing text still cites the original Safe-to-Spend (₹2,840) after a commitment is added (hero updates live to the new value). Flagged in HANDOFF.md for a decision.

**Next:** [T] Acceptance Testing of the Scenario 01 prototype, and/or prototype Scenarios 02 & 03.

---

### 2026-07-08 — Phase 5: Prototyping — Authentication Flow Rework + Upload Validation

**Agent:** Claude Code (WDS Phase 5 Implementation Partner)
**Requested by:** ALPHA (detailed spec with acceptance criteria)

**Implemented (all client-side simulation — no backend — verified 24/24 via CDP, zero console errors):**
1. **Login-first flow** — new `index.html` entry → Login. `01.2-login.html` rewritten from the auto-auth transition into the real **Login landing page** (email/password, "Register User", "Forgot password?"). Auto-login removed.
2. **Register rework** (`01.1`) — client + simulated server-side validation, **unique-email** check, and a **"Registration successful → Return to Login"** success state. No session created on register (manual login required).
3. **Mock auth backend** (`shared/auth.js`) — `localStorage` user "DB" (seeded `priya@example.com`/`priya123`), `sessionStorage` session (60-min TTL), register/login/resetPassword/logout, `requireAuth`/`redirectIfAuthed` guards.
4. **Session management + protected routes** — inline `<head>` guard on Upload, Transactions, Dashboard, Insights, Copilot (blocks direct-URL/unauthenticated access → Login) + `Auth.requireAuth()`.
5. **Logout** — left-nav footer (app screens) + Upload header; clears session → Login; post-logout access blocked.
6. **Forgot Password** — reset workflow (demo sets a new password; production would email a signed link).
7. **Statement upload validation** (`01.3`) — **PDF + CSV only**; extension + MIME + empty + size (10 MB) + content-sniff (PDF `%PDF-` header, CSV text/columns) + simulated server-validate; friendly errors for invalid type / empty / corrupted / unsupported format / parse failure / server / network.

**Docs updated:** `README.md` (flow, demo creds, Authentication section), `HANDOFF.md` (auth + file-validation deltas, production auth-security notes).

**Note:** This is a faithful *client-side simulation*; a production backend must hash passwords, use httpOnly session cookies, and re-validate everything server-side (documented in HANDOFF.md).

**Next:** [T] Acceptance Testing against the auth acceptance criteria, and/or prototype Scenarios 02 & 03.

---

### 2026-07-08 — Phase 5: Prototyping — Logout UI/UX Polish

**Agent:** Claude Code (WDS Phase 5 Implementation Partner)
**Requested by:** ALPHA
**Scope:** CSS-only refinement of the logout controls added in the auth rework (no logic change).

**Changes (verified via CDP hover screenshots, zero console errors):**
- **Sidebar logout** (all 4 app screens) — footer action with a top divider, inset/rounded like the nav tabs; hover is now **solid teal + white text/icon** (matches the primary buttons), fixing a washed-out teal-on-tint hover and a CSS specificity conflict where a generic nav-tab hover was overriding it.
- **Upload header logout** — upgraded from plain muted text to a **secondary-style pill button** (⏻ Log out) that also hovers to solid teal + white.
- Added pointer cursor + neutral hover to the nav tabs for consistent button feel.

**Rationale:** align the logout with the app's established design language (brand teal, primary/secondary button styles) so it reads as a clear, high-contrast action rather than a faint/inconsistent element.

**Files:** `shared/styles.css` (logout + nav-tab hover), `01.3-statement-upload.html` (header logout markup). Prototype-only; no page-spec changes.

**Next:** [T] Acceptance Testing, and/or prototype Scenarios 02 & 03.

---

### 2026-07-09 — Phase 5: Prototyping — Desktop-Only Reconciliation + Scenario 02 (Commitments Management) Built

**Agent:** Claude Code (WDS Phase 5 Implementation Partner)
**Activity:** [P] Prototyping — updating the existing Scenario 01 prototype to match two spec changes made the same day: the architecture spine resolving PRD open item X1 (MVP is desktop-only, non-responsive — mobile/responsive deferred to an optional future phase), and `00-ux-scenarios.md`'s scope correction promoting Commitments Management (02.1) from P2 to committed P1 (the Dashboard already depended on it for Safe-to-Spend ring-fencing and the "+Add a commitment" CTA), plus reinstating the Confidence Score Drill-In Panel as committed scope (epics.md Story 5.2 — it had been marked deferred in the Phase 3 scenario outline, but was never actually cut from the build backlog).

**Changes:**
1. **Desktop-only sidebar** — `shared/styles.css` / `shared/nav.js`: removed the 76px mobile icon-rail variant and its `@media (min-width:768px)` breakpoint; the left sidebar is now always the full 208px labeled rail. Added "Commitments" as a fifth persistent nav item (Dashboard · Transactions · Commitments · Insights · Copilot), reconciling the mobile-bottom-nav set (missing Insights) and the `ux-spec-mvp.md` sidebar draft (missing Commitments) per `01.5-dashboard.md`'s `dashboard-sidebar-nav` note.
2. **Commitments Management built** (`02.1-commitments-management.html`, new) — full page per the `02.1-commitments-management.md` spec: Safe-to-Spend impact bar ("Protecting ₹X" / "Safe to spend ₹Y"), commitment list with criticality icon/due-day/amount/"…" actions menu, Add/Edit modal (name, amount, due-day, criticality — "Protect this commitment"), delete confirmation dialog, empty state, Escape/backdrop/× dismiss, focus-to-first-field on open.
3. **Shared commitment state** (`shared/commitments.js`, new) — commitments now persist in `localStorage` (`afc_commitments`), seeded from `demo-data.json`, and are read/written by both the Dashboard and the Commitments page, so adding/editing/deleting a commitment on one page is reflected on the other. Reconciles the prior HANDOFF.md divergence where the Dashboard's "+Add a commitment" opened an inline modal because Scenario 02 wasn't built yet — it now navigates to `/commitments` per the original page spec, and the Dashboard's inline modal was removed (superseded by the dedicated page).
4. **Confidence Score Drill-In Panel** (`01.5-dashboard.html`) — replaced the plain tooltip with a panel (`dashboard-hero-confidence-drillin`) showing the Prediction Confidence summary plus a reverse-chronological `score_events` list (delta, explanation, time elapsed), per the updated `01.5-dashboard.md` spec. Confidence labels relabelled per spec: High/Medium/Low → Well prepared/On track/Watch this (demo data currently exercises "On track"); the raw score is still never rendered.
5. **Demo data** (`data/demo-data.json`) — added `score_events` (4 entries); relabelled `confidence.level`/`.tooltip` to the new label set; removed the unused inert `c4` "suggested" commitment placeholder.

**Verification:** headless Chrome + raw DevTools Protocol (no `puppeteer` package available offline, so driven directly over the CDP WebSocket) — logged in via `Auth.login()`, then exercised: sidebar renders all 5 items at 208px on every authenticated page; confidence chip opens/closes the Drill-In panel showing all 4 `score_events`; Dashboard → Commitments navigation; add/edit/delete commitment flows (impact bar and Safe-to-Spend chip update correctly: base ₹18,000/₹2,840 → +₹1,800 add → ₹19,800/₹1,040 → edit +₹500 → ₹20,300/₹540 → delete −₹7,000 → ₹13,300/₹7,540, all arithmetically consistent); Escape-key modal dismiss; newly-added commitment reflected in the Dashboard's Safe-to-Spend and timeline on return. Zero console errors/exceptions across every page tested.

**Docs updated:** `HANDOFF.md` (divergence table reconciled — Commitments/nav rows resolved and removed, new commitment-persistence and API rows added), `PROTOTYPE-ROADMAP.md` (device compatibility → desktop-only, 02.1 added to build sequence), `README.md` (8 screens, desktop-only framing, structure, honesty-layer wording).

**Next:** [T] Acceptance Testing against the 02.1 spec's acceptance criteria and the resolved desktop-only decision; prototype Scenario 03 (Copilot return-visit).

---

### 2026-07-09 — Phase 5: Prototyping — Asset Refresh (Screenshots + Content-Column Widths)

**Agent:** Claude Code (WDS Phase 5 Implementation Partner)
**Activity:** [P] Prototyping — follow-up to the same-day desktop-only reconciliation, closing the loop on the prototype's `assets/` screenshot set and remaining mobile-viewport-shaped layout.

**Changes:**
1. **Content columns widened** for a genuine desktop reading width instead of a stretched mobile layout: `.page--flow` 560→680px, `.dash` 560→760px, `.copilot-thread`/`.copilot-input-bar` 560→720px, `.auth-card` 420→440px (unifying the two prior breakpoint-gated values into one). Removed the now-dead `@media (min-width:768px)` / `(min-width:1280px)` rules these values used to live behind — the prototype has no breakpoints left.
2. **Screenshot set refreshed** (`assets/`) — of the pre-existing ~44 screenshots, 19 were mobile-viewport captures (390–872px wide) or showed the old 4-item nav / "Medium" confidence label; all were either regenerated at the 1440×900 desktop baseline or removed as redundant historical iteration duplicates once a canonical current-state shot existed. Added 3 new screenshots for previously-undocumented desktop-only UI: `dashboard-confidence-drillin.png`, `commitments-default.png`, `commitments-add-modal.png`.
3. **Verification:** re-ran the headless-Chrome/CDP sweep across all 9 pages at 1440×900 after the width changes — zero console errors, zero horizontal overflow on every page.

**Artifacts Updated:** `shared/styles.css`, `assets/*.png` (regenerated/removed set), `README.md` (verification note).
**Next:** Unchanged from the prior entry — [T] Acceptance Testing, then Scenario 03.

---

### 2026-07-09 — Phase 5: Prototyping — Navigation Flow Update (Dashboard as Landing Page) + Fluid Responsive Layout

**Agent:** Claude Code (WDS Phase 5 Implementation Partner)
**Activity:** [P] Prototyping — direct user requirement, not a Steps-30–34 spec propagation this time (the request originated the change; specs were updated afterward to match, per the user's explicit choice).
**Requested by:** ALPHA

**Requirement:** Re-sequence the golden path so the Dashboard, not the Transactions Table, is the default landing page immediately after Statement Upload; add a prominent "View All Transactions" CTA on the Dashboard; keep all 5 authenticated screens freely reachable from the sidebar with the active item highlighted; and make every authenticated screen's layout genuinely fluid — filling the available browser window on laptop/desktop resolutions (1366×768–1920×1080+) rather than sitting in a fixed-width column, with dashboard/table/chart content resizing responsively and no horizontal scroll.

**Clarified via 3 questions before starting** (since the request's own nav diagram conflicted with recently-committed scope): (1) "Safe-to-Spend" stays the Dashboard's hero section, not a new standalone page; (2) Commitments stays in the sidebar (the request's nav list omitting it was an oversight, not a request to cut committed P1 scope); (3) update the WDS specs to match, not just the prototype code.

**Changes:**
1. **Flow re-sequenced** — `01.3-statement-upload.html`'s completion CTA retargeted from `/transactions` to `/dashboard`, relabeled "Go to my Dashboard →" (was "Review my transactions"). `shared/nav.js`'s `SCENARIO_ORDER` updated to match.
2. **New Dashboard CTA** — `dashboard-transactions-cta` card ("Review your transactions" / dynamic transaction-count text / "View All Transactions →" button → `/transactions`), added to the below-fold grid.
3. **Dashboard restructured into a responsive card grid** — Morning Briefing, the new Transactions CTA, Spending Breakdown, and Commitments Timeline now render as `.dash-card`s in a `.dash-grid` (`display:grid; grid-template-columns: repeat(auto-fit, minmax(340px,1fr))`), reflowing from 1 to 4 columns as the window widens — instead of one stacked column. The hero card keeps a contained 960px max-width (it's a focal number, not a data panel); the below-fold grid fills the rest.
4. **Insights page** — `#insights-list` given the same `auto-fit` grid treatment (`minmax(420px,1fr)`) so cards sit 2-up on wide screens instead of one narrow stacked column.
5. **Fluid content columns everywhere** — `.dash`/`.page--flow.has-sidenav` (Dashboard, Transactions, Insights, Commitments) now cap at 1680px and fill the window between the sidebar and that cap; `.copilot-thread`/`.copilot-input-bar` widened 720→960px; `.commit-content` (Commitments page) capped at 960px so its list/form stays a focused reading width even inside the wide `.dash` column. `.page--flow` (Upload only, no sidebar) stays at 720px — a single-step task screen, deliberately not full-bleed.
6. **Bug found and fixed during verification:** the first pass of the fluid-width change (`width:100%` + `margin:0 auto` combined with a fixed `margin-left:208px` for the sidebar offset) caused horizontal overflow at 1366×768 and 1440×900 — the `width:100%` computed against the *full* viewport before the sidebar margin was subtracted, double-counting the 208px. Fixed by removing `width`/`margin:auto` and relying on default `width:auto` box-model math (`margin-left:208px` fixed, `margin-right:0`, `max-width` cap) — this correctly derives width as `min(viewport − 208px, cap)` with no overflow possible.
7. **Second bug found and fixed:** narrowing the Insights cards (via the new 2-column grid) exposed a pre-existing latent issue — `.btn`'s `width:100%` caused the "Ask the Copilot about this" secondary button to claim its entire flex row, wrapping the sibling "Got it" dismiss button onto two lines. Fixed with `.insight-actions .btn { width:auto; flex:0 0 auto; }` and `white-space:nowrap` on `.insight-dismiss`.

**Verification:** headless Chrome over the raw CDP WebSocket. **Flow:** logged in → Upload → sample statement → parse completes → clicked "Go to my Dashboard →" → landed on `/01.5-dashboard.html` with "Dashboard" highlighted in the sidebar → clicked "View All Transactions" → landed on `/01.4-transactions-table.html` with "Transactions" highlighted → hopped freely through Commitments → Insights → Copilot → Dashboard via the sidebar, confirming correct URL and active-item highlighting at every stop. **Responsive sweep:** all 8 authenticated+public pages at 1366×768, 1440×900, and 1920×1080 — **zero console errors, zero horizontal overflow** at every page/resolution combination (24 checks total) after the two bug fixes above. Visually confirmed via screenshot that the Dashboard's 4-card grid fills a single row at 1920px and reflows to 3 columns at 1440px / narrower at 1366px.

**Docs/specs updated:** `_bmad-output/C-UX-Scenarios/00-ux-scenarios.md`, `01-priyas-first-honest-morning.md` (Q8 shortest path + Scenario Steps table), `01.3-statement-upload.md` (Exit Points, CTA object spec, ASCII diagram, Related Pages, Page States), `01.4-transactions-table.md` (Entry Points, Previous/Next Step, Related Pages, Technical Notes), `01.5-dashboard.md` (Entry/Exit Points, new `dashboard-transactions-cta` + `dashboard-below-fold-grid` sections, ASCII layout diagram, Technical Notes), `_bmad-output/planning-artifacts/prd.md` (golden-path line). Prototype docs: `HANDOFF.md`, `PROTOTYPE-ROADMAP.md`, `README.md`. Screenshot set in `assets/` refreshed to match (new grid layout, new CTA card, updated button label; added `dashboard-wide-1920.png`).

**Next:** [T] Acceptance Testing against the updated flow/layout requirements; prototype Scenario 03 (Copilot return-visit).

---

### 2026-07-09 — Phase 5: Prototyping — Sidebar Nav Simplified to 4 Items + Embedded Fallback Data

**Agent:** Claude Code (WDS Phase 5 Implementation Partner)
**Requested by:** ALPHA — two requests: (1) remove Commitments from the sidebar, keep it as the existing Dashboard button/link; (2) "my current html pages don't have any data in it" — add dummy data and show the result.

**Change 1 — Commitments removed from the sidebar:** `shared/nav.js`'s `renderSideNav()` reverted to the 4-item set (Dashboard, Transactions, Insights, Copilot) — matching `epics.md` FR-6.4 exactly, which had said 4 screens all along. This reverts the 5th-item addition made earlier the same day (in the desktop-only reconciliation step), which had over-corrected past what FR-6.4 actually specifies. Commitments Management remains fully committed P1 scope, unchanged — only its navigation entry point changes back to what it always was: the Dashboard's "+ Add a commitment" link (`dashboard-commitments-add`, already pointed at `02.1-commitments-management.html`, no change needed there). `01.5-dashboard.md` and `02.1-commitments-management.md` updated to match (Entry/Exit Points, sidebar-nav object spec, ASCII diagrams); `01.6`/`01.7`/`01-priyas-first-honest-morning.md`'s stray "…Commitments…" mentions in their own sidebar descriptions corrected too.

**Change 2 — root-caused the "no data" report:** Investigated rather than guessed. Root cause: `shared/data.js`'s `loadDemoData()` fetches `data/demo-data.json`, which only works when the prototype is served over http — if a page is opened directly from disk (`file://`, e.g. double-clicking the HTML in File Explorer), the browser blocks that `fetch()` and the previous code just logged an error and left the page showing its default placeholder state (₹0, empty lists) — exactly the "no data" symptom described. **Fix:** `loadDemoData()` now catches the fetch failure and falls back to `FALLBACK_DEMO_DATA`, an embedded copy of the same dataset living directly in `data.js`, so every page shows full data regardless of how it's opened. Confirmed via headless Chrome: navigated directly to `file:///.../01.5-dashboard.html` (bypassing the local server entirely) and verified the hero (₹2,840), briefing text, and 7-category donut legend all populate correctly from the fallback, with a console warning (not error) explaining what happened and how to get the real fetch path (`python -m http.server 8000`).

**Verification:** headless Chrome/CDP. Confirmed the 4-item sidebar renders identically on all pages that use it; confirmed `dashboard-commitments-add` still navigates to the Commitments page; confirmed the Commitments page itself renders the same 4-item sidebar with no active item (correct, since it isn't one of the 4 destinations); confirmed data renders identically whether fetched over http or served from the `file://` fallback path. Screenshots refreshed: `dashboard-full.png`, `final-dashboard-desktop.png`, `commitments-default.png`; added `dashboard-file-protocol-fallback.png` as evidence of the fallback working.

**Docs updated:** `HANDOFF.md`, `README.md` (nav description, `Run it` section documents the fallback behavior, `data.js` line in Structure). `_bmad-output/C-UX-Scenarios/{01-priyas-first-honest-morning.md, 01.5-dashboard.md, 01.6-ai-insights-recommendations.md, 01.7-copilot-chat.md, 02-priya-protects-what-matters/02.1-commitments-management.md}`.

**Next:** [T] Acceptance Testing; prototype Scenario 03 (Copilot return-visit).

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
| 2026-07-08 | Prototype fidelity upgraded Gray Model → branded teal theme (tokens in `shared/styles.css`) | Phase 5: Prototyping | Claude Code + ALPHA |
| 2026-07-08 | Persistent left nav on all authenticated app screens; nav = Transactions · Dashboard · Insights · Copilot Chat (the "Commitments" slot repurposed to Insights → `01.6`, since the Commitments page is unbuilt Scenario 02) | Phase 5: Prototyping | Claude Code + ALPHA |
| 2026-07-08 | Dashboard "+ Add a commitment" realized as an inline modal form that updates Safe-to-Spend live — brings Scenario-02's "protection payoff" moment onto the Dashboard prototype | Phase 5: Prototyping | Claude Code + ALPHA |
| 2026-07-08 | Auth reworked to login-first: `index.html`→Login landing; register no longer auto-logs in (success → "Return to Login"); mock auth backend in `shared/auth.js` (localStorage DB + sessionStorage session); protected routes guarded; logout added | Phase 5: Prototyping | Claude Code + ALPHA |
| 2026-07-08 | Statement upload accepts PDF **and CSV** (was PDF-only) with full client-side validation (type/MIME/size/empty/corrupt/format) + friendly errors; server must re-validate in production | Phase 5: Prototyping | Claude Code + ALPHA |
| 2026-07-09 | PRD open item X1 resolved: Phase 1 MVP is **desktop-only** (localhost, single-user, 1280px+, non-responsive); mobile-responsive web moved to optional/future-phase, no longer a Phase-1 carry-forward blocker | Architecture | ALPHA |
| 2026-07-09 | Commitments Management (02.1) promoted from P2 to **committed P1 scope**; Confidence Score Drill-In Panel (epics.md Story 5.2) reinstated as committed scope (had been marked deferred in the Phase 3 outline, but was never actually cut from the build backlog) | UX-Scenarios scope correction | ALPHA |
| 2026-07-09 | Prototype updated to match: sidebar is desktop-only 208px rail everywhere (mobile icon-rail variant removed); Commitments Management built as a full page with shared, `localStorage`-persisted commitment state; Dashboard's confidence tooltip replaced with the Drill-In panel | Phase 5: Prototyping | Claude Code |
| 2026-07-09 | Golden path re-sequenced: Dashboard (not Transactions Table) is now the default landing page immediately after Statement Upload; Transactions is reached via a new "View All Transactions" Dashboard CTA. PRD/UX-Scenarios/page specs updated to match, at ALPHA's explicit direction, rather than leaving the specs stale | Phase 5: Prototyping | Claude Code + ALPHA |
| 2026-07-09 | Authenticated-screen layouts made fluid (fill the window up to a 1680px cap) instead of fixed-width; Dashboard and Insights below-fold content laid out as a responsive CSS Grid card layout (`auto-fit`) instead of one stacked column | Phase 5: Prototyping | Claude Code + ALPHA |

---

## About This Folder

- **This file** — Single source of truth for project progress
- **agent-experiences/** — Compressed insights from design discussions (dated files)
- **wds-project-outline.yaml** — Project configuration from Phase 0 setup (not yet run for this project)
