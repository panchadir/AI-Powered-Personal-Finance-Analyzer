---
stepsCompleted: ["step-01", "step-02", "step-03", "step-04"]
inputDocuments:
  - "_bmad-output/planning-artifacts/prd.md"
  - "_bmad-output/planning-artifacts/architecture/architecture-AI-Powered-Personal-Finance-Analyzer-2026-07-08/ARCHITECTURE-SPINE.md"
  - "_bmad-output/planning-artifacts/ux-spec-mvp.md"
---

# AI-Powered Personal Finance Analyzer - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for AI-Powered Personal Finance Analyzer, decomposing the requirements from the PRD, UX Design spec, and Architecture Spine into implementable stories.

## Requirements Inventory

### Functional Requirements

FR-1.1: Register with email + password; bcrypt-hashed, never stored plaintext; auth token in httpOnly cookie (not localStorage) for DPDP compliance and XSS protection.
FR-1.2: Registration creates the account and shows a `"Registration successful → Return to Login"` confirmation panel — no auto-login, no session, no auto-redirect (product decision 2026-07-09, supersedes the original auto-login intent); the user logs in to reach Upload. No email verification for MVP.
FR-1.3: User can log in and log out; protected pages redirect unauthenticated users to login.
FR-1.4: All data scoped to user_id; no cross-user data access. A test asserts this — no IDOR walks into Phase 2.
FR-1.5: Trust signal ("No guessing. No shame.") appears above the form fields — functionally required, removal fails acceptance. Password field includes a show/hide toggle.
FR-1.6: "Email already registered" error embeds an inline "Log in instead?" link.
FR-1.7: T&C and Privacy links open in an in-page modal (not a new tab); no pre-ticked consent checkboxes (DPDP Rule 4).
FR-1.8: Validation fires on blur, clears on input — on-submit-only validation is not acceptable.
FR-1.9: Registration-success confirmation: the panel replaces the form with `role="status"` and `aria-live="assertive"` on the `"Registration successful!"` headline, and offers a `"Return to Login"` action; no session is created and no auto-redirect occurs (no-auto-login, product decision 2026-07-09).

FR-2.1: Upload CSV bank statement; map columns to the canonical transaction schema (≥2 common Indian-bank CSV shapes supported).
FR-2.2: Upload text-based PDF; extract via statementsparser → pdfplumber → camelot → LLM-text fallback.
FR-2.3: Normalize to canonical schema, de-duplicate (hash of date+amount+description), persist.
FR-2.4: Scanned/image PDF detected and honestly refused with plain-language message — no silent failure.
FR-2.5: Upload screen framed as "Step 1 of 3" (Upload → Review → Dashboard) — functional onboarding contract, not decoration.
FR-2.6: Parse progress shows 4 named real-server-state steps: Reading PDF → Identifying Transactions → Categorising by Rules → AI Assist. Transport: WebSocket push preferred; 1-second polling as MVP fallback.
FR-2.7: Completion summary shows honesty breakdown: "{n} by rules · {n} by AI · {n} need your help" — derived from real parse output, not placeholders.
FR-2.8: "Review transactions" CTA is aria-disabled (not hidden) until parse completes; stays in tab order.
FR-2.9: Parse failure shows empathetic copy plus a contact/support link — not a generic error toast.
FR-2.10: Back navigation mid-upload prompts a confirmation if upload is in progress.

FR-3.1: Tier-1 rules engine — deterministic keyword/merchant-pattern matching for common Indian transactions; instant, free.
FR-3.2: Tier-2 LLM — uncategorized transactions → Claude claude-haiku-4-5 with structured-output schema (category enum + confidence + reasoning). Enum is hard-constrained — no invented categories.
FR-3.3: Every transaction stores category_source (rule|llm|user) and category_confidence.
FR-3.4: Tier-3 ("Teach Me") — user correction writes a merchant-level rule; "Re-apply to all matching merchants" toggle defaults ON; persists for future uploads.
FR-3.5: Confidence badge system: needs_review → amber "?" badge; ai_categorised → blue "AI" badge; rule_categorised → no badge. Raw confidence percentages must never be shown.
FR-3.6: Filter chips dynamically generated from actual parsed categories; "Needs review" chip always present when count > 0.
FR-3.7: Transaction list uses virtual scroll — standard DOM list not acceptable for 100–300 rows without layout thrash on a standard developer machine.
FR-3.8: "Needs review" banner uses amber tone, not error red.
FR-3.9: "See my Dashboard" CTA always enabled (sticky) — user never blocked in review loop.
FR-3.10: Credit/income rows visually distinguished with green treatment.

FR-4.1: Safe-to-Spend formula: safe_to_spend_today = max(0, (available_balance − reserved_total − buffer) ÷ days_until_next_confirmed_income). Rounded down to nearest ₹10. Never negative.
FR-4.2: Reservation Rule (DD-1): Known commitments due on-or-before next income always fully reserved; predicted commitments reserved only inside criticality proximity window; variable-amount reserves top of range; commitment due on income day reserved against current balance unless income confidence is High AND income ≥ commitment.
FR-4.3: Commitment criticality tiers: Critical (7-day window), Important (5-day window), Flexible (3-day window). New commitments default to Important.
FR-4.4: Buffer default ₹2,000, configurable per user. All engine tests state buffer explicitly.
FR-4.5: Two-layer display: "Today: ₹X" and "After confirmed income on {date}: ₹Y" — these two figures must never be merged.
FR-4.6: Conservative under uncertainty: variable bills reserve top-of-range; missing data lowers Prediction Confidence, never inflates Safe-to-Spend.
FR-4.7: Freshness caveat displayed on the hero card itself: "based on your statement up to {statement end date}."
FR-4.8: Undetected salary fallback: shows "We couldn't detect a salary — add one manually?" — not a zero or error.
FR-4.9: Shortfall state: Safe-to-Spend floored to ₹0; honest shortfall message surfaces.
FR-4.10: Live update — Safe-to-Spend recalculates in hero card when commitment added/edited/deleted, without full page reload.
FR-4.11: Briefing narration = snapshot at generation time; hero card = live. Intentional.
FR-4.12: Engine output struct: {reserved_total, spendable_pool, days_to_income, safe_to_spend_today, safe_to_spend_after_income (nullable), prediction_confidence (Low|Medium|High), drivers[], data_quality_flags[], safety_ok}.

FR-5.1: Confidence Score (0–100) measures financial preparedness only — never app engagement.
FR-5.2: Prediction Confidence (Low|Medium|High) measures data completeness — shown alongside the Score, never conflated with it.
FR-5.3: Event-to-explanation binding: every score change writes a score_events row (delta, trigger_event, explanation, suggested_action).
FR-5.4: Cold start: compute immediately; Prediction Confidence = Low/Medium with stated reason. "Confidence grows with more data" framing.
FR-5.5: Confidence chip interaction: tapping the chip surfaces an inline tooltip with distinct copy per level. Raw score numbers are never displayed.
FR-5.6: "Why?" expandable block: expandable on the hero card showing 1–2 sentence explanation traceable to real data.
FR-5.7: Stale data warning: when statement data is >30 days old, amber banner above hero card prompts re-upload.
FR-5.8: Counter-metric — over-conservatism guard: if Safe-to-Spend is ₹0 on a statement with a positive balance and no commitments due this cycle, that is a bug. A test must assert a commitment-free, buffer-covered balance produces non-zero STS.

FR-6.1 (P0): Hero-first layout: Safe-to-Spend card and Confidence chip always above the fold; charts below.
FR-6.2 (P0): Plain-language briefing narrated by Claude — honest, calm, non-judgmental, jargon-free; confidence caveat never buried.
FR-6.3 (P1): Briefing follows Observation → Evidence → Explanation → Action shape.
FR-6.4 (P0): Persistent left nav across all four app screens (Transactions / Dashboard / Insights / Copilot).
FR-6.5 (P0): "+ Add a commitment" on the Dashboard navigates to the dedicated Commitments Management page (WDS screen 02.1) — a list of commitments with per-row Edit/Delete, a Safe-to-Spend impact bar, and an add/edit modal on that page (name / amount / due-date / criticality). On save, Safe-to-Spend updates live per FR-4.10.

FR-7.1 (P0): Chat interface; responses stream token-by-token.
FR-7.2 (P0): Copilot answers using read-only tools over real data — never invents numbers, never performs a financial action.
FR-7.3 (P0): Hardcoded LLM system-prompt rules (non-configurable): (1) Never invent financial figures; (2) Express uncertainty explicitly; (3) Never give investment recommendations; (4) Always populate trace field.
FR-7.4 (P0): SSE event schema: token, trace, done.
FR-7.5 (P0): Trace chips: every data-citing response shows "Based on: …" chips below the bubble.
FR-7.6 (P0): "I don't know" as a valid response — insufficient-data queries return graceful honest response.
FR-7.7 (P1): Quick-prompt buttons (e.g., "Can I afford ₹___ this weekend?").
FR-7.8 (P1): Context handoff from Insights: pre-populated input + "Talking about: {pattern name}" dismissable chip; insight_id in POST body.
FR-7.9 (P1): Chat history stored server-side (not localStorage), scoped to user_id.
FR-7.10 (P1): Accessibility: role="log" + aria-live="polite" on chat thread; stream announces completed sentences; send button uses aria-disabled.

FR-8.1 (P0): Deterministic pandas detectors surface ≥3 named patterns from: post-payday spike, death-by-small-purchases, zombie subscriptions, weekend-vs-weekday pace, upcoming-commitment collision. All five detectors must be coded; ≥3 must fire on demo statement.
FR-8.2 (P0): Each insight narrated in Observation → Evidence → Explanation → Action shape. Evidence must cite 2–3 exact data points (specific dates, merchant names, exact amounts) in a visually distinct evidence block.
FR-8.3 (P0): SEBI IA boundary on Action layer: Action may suggest the user consider a change; it must never prescribe.
FR-8.4 (P0): Insight lifecycle: seen (soft fade), dismissed (POST /insights/{id}/dismiss; moves to collapsed section), all dismissed empty state (graceful copy), insufficient data (<30 transactions) positive framing.
FR-8.5 (P0): When data_months < 3, footer note: "More data sharpens these patterns."
FR-8.6 (P1): Insights woven into the briefing.

FR-9.1 (P1): Detect recurring obligations (similar amount ±10%, ~monthly cadence); proactively surface for user confirmation.
FR-9.2 (P1): User can add/edit/delete commitment: name, amount, due-day, criticality (Critical / Important / Flexible). Default: Important.
FR-9.3 (P1): due_day=31 maps to last day of shorter months; displayed as "end of month."
FR-9.4 (P1): POST /commitments and PATCH /commitments/{id} responses include safe_to_spend_updated so the Commitments page updates its Safe-to-Spend impact bar (and the Dashboard reflects it) without a separate fetch.

### NonFunctional Requirements

NFR-1: Honesty & safety (hard): no displayed number may cause a missed committed obligation; conservative-by-default; any pipeline failure degrades to a visible, plainly-worded state — never a silent wrong number. LLM must not be in the computation path for Safe-to-Spend or Confidence Score.
NFR-2: Local & single-user: runs on `reflex run`; no cloud accounts required; data in a local PostgreSQL 16 instance (docker-compose service `db`). SQLite is test-only.
NFR-3: Separation of computation & narration: all money math is deterministic, unit-tested Python in services/engine/; LLM confined to language in services/narrate/. This boundary is architectural, not stylistic.
NFR-4: Cost & model routing: total Claude API spend for build + demo cycle < $15. claude-haiku-4-5 for Tier-2 categorization; claude-opus-4-8 (or claude-sonnet-5 as cost lever) for briefing narration and Copilot. Batch API for bulk categorization; prompt caching for system prompts (~90% saving on cached portion).
NFR-5: Privacy/provenance: data stays local; only transaction text needed for categorization/Q&A sent to Claude API; UI states this boundary. Secrets in .env (git-ignored). Auth token in httpOnly cookie.
NFR-6: Migratability: business logic in framework-agnostic services/; Reflex State orchestrates only. PostgreSQL is already the Phase-1 store; Phase 2 (FastAPI, WhatsApp/AA) is a re-skin, not a rewrite.
NFR-7: Localization format: formatINR() (Indian number grouping: ₹1,25,000) and formatDate() (ISO → "30 Jun 2026") are required shared utilities used in all currency and date displays. Non-standard formatting fails acceptance.
NFR-8: Accessibility baseline: role="log" + aria-live="polite" on Copilot chat thread; aria-live="assertive" on the registration-success confirmation headline; aria-disabled (not disabled) on not-yet-active CTAs.
NFR-9: Performance baseline: statement parse completes in <60s for a standard 3-month PDF on a developer laptop. Dashboard initial render <3s after parse.

### Additional Requirements

- **Starter template**: `reflex init` + project skeleton setup (pages, services/{ingestion,categorize,engine,narrate}/, models.py, .env, requirements.txt) is the foundation for Epic 1 Story 1.
- **Source tree structure (AD-2, AD-14):** `finance_app/` (Reflex app root) + `services/` (framework-agnostic Python, NO reflex imports) + `tests/` + `data/` layout must be established on Day 1, along with `docker-compose.yml` (PostgreSQL 16, service `db`) and `alembic/` migrations (Postgres is the Phase-1 store).
- **`pytest services/engine/` is the non-negotiable MVP quality gate** — must run with zero LLM calls; enforced by a raising fixture (AD-1).
- **Golden-file ingestion tests** — one fixture per supported bank format (CSV + HDFC PDF) in `tests/ingestion/`.
- **IDOR test required (AD-4)** — a dedicated test asserts user A cannot read user B's transactions, commitments, or chat history; must pass before Phase 2.
- **Canonical dedup key (seam):** `(user_id, date, amount, description_raw, balance_after)` — decided once in `services/ingestion/`, normalized before comparison (ISO date, trimmed description, abs(amount)).
- **STS denominator guard (seam):** `days_until_next_confirmed_income` can be 0 or undefined — guard before dividing; fallback to reserved-only / "add your payday" prompt, never divide by zero.
- **SSE done in finally (seam):** Copilot stream emits `done` from a `finally` block; explicit error frame if LLM stream raises mid-token.
- **Prompt injection guard for DB text (seam):** `description_raw` / `merchant_normalized` enter Copilot/narration prompts as delimited quoted data, never concatenated into the system prompt.
- **Decimal/integer arithmetic (AD-8 guard):** All engine arithmetic uses `Decimal` (or integer paise), never `float`. `float` is display-only.
- **Reflex go/no-go checkpoint at Day 2 noon** — if `rx.State` reactivity is still blocking, invoke Streamlit escape hatch.
- **Pin Reflex + reflex-local-auth versions in requirements.txt on Day 1.**
- **Validate statementsparser covers HDFC demo format Day 1, Hour 1 (flagged assumption).**
- **demo-data.json validation Day 1** — confirm ≥3 insight detectors fire on the 24-transaction June 2026 Priya dataset.

### UX Design Requirements

UX-DR1: Hero-first dashboard layout — Safe-to-Spend card and Confidence chip must be above the fold; charts (rx.plotly donut/bar) positioned below the fold as supporting evidence, never leading.
UX-DR2: Confidence Score chip displays label only ("Well prepared" / "On track" / "Watch this") — raw score number (e.g. 87) must never be displayed anywhere in the UI.
UX-DR3: Two-layer Safe-to-Spend display — "Today: ₹X" and "After your salary on {date}: ₹Y" rendered as visually distinct rows, never merged into one figure.
UX-DR4: Freshness caveat on the hero card itself — "Based on your statement up to {date}" text rendered on the hero card, not in a footer or tooltip.
UX-DR5: Persistent left sidebar navigation (~200px width) on all 4 app screens: Transactions / Dashboard / Insights / Copilot. Must be present in all page layouts.
UX-DR6: "Step 1 of 3" step indicator (Upload → Review → Dashboard) visible on the Upload page — functional onboarding contract, not decoration.
UX-DR7: Microcopy tone contract — all generated and static copy must be: honest, calm, non-judgmental, plain-language, warm-not-saccharine. Specific approved/banned copy pairs per the microcopy sheet (e.g. "I can't read this one…" not "Error: no text layer").
UX-DR8: Observation framing throughout — "We noticed…" / "Your spending pace picked up…" not "You overspent…". Zero shame-adjacent language.
UX-DR9: "Teach Me" confirmation copy — "Got it — I'll call Swiggy 'Dining' from now on." pattern, not generic "Category updated successfully."
UX-DR10: Confidence Score drill-in panel — reached from score chip; shows Prediction Confidence label + reason + score_events list (delta, event, days-ago); every row = a real event row; no unexplained changes visible.
UX-DR11: Shortfall state copy — "Your committed bills before payday come to ₹X more than your balance. Here's what I'd protect first." — not "Insufficient funds."
UX-DR12: Empty dashboard state — "Upload a statement and I'll show you what's safe to spend — and why." — not "No data available."
UX-DR13: "Needs review" categorization banner uses amber tone (not error red).
UX-DR14: Credit/income transaction rows visually distinguished with green treatment.
UX-DR15: Amber stale-data banner above hero card when statement end date is >30 days before today, prompting re-upload.
UX-DR16: Copilot chat UI — streaming token-by-token display; role="log" + aria-live="polite" on chat thread; send button uses aria-disabled; quick-prompt buttons ("Can I afford ₹___?") below input.
UX-DR17: "Show me why" drill-in button label (not "View details") — on the hero card freshness caveat.
UX-DR18: Briefing panel — 2–4 sentence calm narrative above chart section; Observation → Evidence → Explanation → Action structure; every number in prose equals engine output exactly.

### FR Coverage Map

| FR | Epic | Description |
|---|---|---|
| FR-1.1 – FR-1.9 | Epic 1 | Auth, registration, session, DPDP compliance, shared utilities |
| FR-2.1 – FR-2.10 | Epic 2 | Upload, PDF/CSV parsing, dedup, progress, honest refusal |
| FR-3.1 – FR-3.10 | Epic 3 | Tier-1/2/3 categorization, badges, virtual scroll, Teach Me |
| FR-4.1 – FR-4.12 | Epic 4 | STS formula, reservation rule, evidence pack struct, pytest suite |
| FR-5.1 – FR-5.8 | Epic 4 | Confidence Score, score_events, cold start, over-conservatism guard |
| FR-6.1 – FR-6.5 | Epic 5 | Dashboard layout, briefing narration, left nav, dedicated Commitments page (02.1) |
| FR-7.1 – FR-7.10 | Epic 6 | Copilot streaming, read-only tools, trace chips, quick prompts |
| FR-8.1 – FR-8.6 | Epic 7 | Insight detectors, evidence blocks, SEBI phrasing, dismiss lifecycle |
| FR-9.1 – FR-9.4 | Epic 5 | Commitment CRUD, recurring detection, live STS update |
| NFR-1 | Epics 4, 8 | Honesty/safety spine + hardening pass |
| NFR-2 | Epic 1 | Local PostgreSQL (docker-compose), reflex run |
| NFR-3 | Epic 4 | Computation/narration separation enforced by pytest |
| NFR-4 | Epics 3, 5, 6 | Model routing constants, prompt caching |
| NFR-5 | Epics 1, 6 | httpOnly cookie, .env secrets, SSE auth seam |
| NFR-6 | All | services/ framework-agnostic throughout |
| NFR-7 | Epic 1 | formatINR/formatDate created in S1.2; used by all subsequent epics |
| NFR-8 | Epics 1, 2, 6 | aria-live, aria-disabled, role="log" |
| NFR-9 | Epics 2, 5 | Parse <60s; dashboard render <3s |

## Epic List

### Epic 1: Secure Access & App Foundation
A user can register, log in, and securely access the application with data scoped to them alone. The project skeleton is live and runnable with all shared utilities in place.
**FRs covered:** FR-1.1, FR-1.2, FR-1.3, FR-1.4, FR-1.5, FR-1.6, FR-1.7, FR-1.8, FR-1.9
**NFRs:** NFR-2, NFR-5, NFR-7, NFR-8
**UX-DRs:** UX-DR5 (persistent left nav skeleton)
**Party-mode finding applied:** `formatINR()` / `formatDate()` created in S1.2 (no downstream story should build them from scratch)

### Epic 2: Statement Upload & Transaction Extraction
A user can upload their bank statement (PDF or CSV) and see a clean, de-duplicated list of transactions with honest progress feedback and an honest refusal for unsupported formats.
**FRs covered:** FR-2.1, FR-2.2, FR-2.3, FR-2.4, FR-2.5, FR-2.6, FR-2.7, FR-2.8, FR-2.9, FR-2.10
**NFRs:** NFR-9 (parse <60s), NFR-6
**UX-DRs:** UX-DR6, UX-DR7, UX-DR8
**Party-mode finding applied:** WebSocket validation is first AC in S2.4; four-step progress bar is a skeleton in Epic 2 — steps 3/4 completed in Epic 3

### Epic 3: Transaction Categorization & Teach Me
A user sees every transaction categorized with provenance badges and can teach the app to correct mistakes, with corrections persisting across future uploads.
**FRs covered:** FR-3.1, FR-3.2, FR-3.3, FR-3.4, FR-3.5, FR-3.6, FR-3.7, FR-3.8, FR-3.9, FR-3.10
**NFRs:** NFR-4 (claude-haiku-4-5), NFR-5
**UX-DRs:** UX-DR9, UX-DR13, UX-DR14
**Party-mode finding applied:** S3.1/S3.2 complete progress bar steps 3/4 (handoff from Epic 2)

### Epic 4: Financial Engine — Safe-to-Spend & Confidence Score ⚠️ HIGH-RISK EPIC
The deterministic engine computes Safe-to-Spend and Confidence Score with a full pytest suite passing across all 12 scenarios. No LLM touches these numbers. This is the product's honesty spine and non-negotiable quality gate.
**FRs covered:** FR-4.1–FR-4.12, FR-5.1–FR-5.8
**NFRs:** NFR-1, NFR-3
**Risk flag:** Largest epic by FR count (20 FRs + 12-scenario pytest suite). No split recommended (shared evidence pack). If bleeding into Day-3 morning, invoke scope-guard cut order immediately.
`
### Epic 5: Dashboard, Briefing & Commitment Management
A user sees their Safe-to-Spend hero card, Confidence Score chip, morning briefing, and charts on a single calm screen — and can add/edit/delete commitments that immediately update the Safe-to-Spend figure.
**FRs covered:** FR-6.1–FR-6.5, FR-9.1–FR-9.4
**NFRs:** NFR-7, NFR-9
**UX-DRs:** UX-DR1, UX-DR2, UX-DR3, UX-DR4, UX-DR10, UX-DR11, UX-DR12, UX-DR15, UX-DR17, UX-DR18
**Consolidation:** FR-9 (Commitments) folded here — same core files as Dashboard, no value without it

### Epic 6: AI Copilot (committed must-ship)
A user can ask natural-language questions about their finances and receive streamed, honest answers that cite real data — never invented numbers — with full trace chips and graceful "I don't know" responses.
**FRs covered:** FR-7.1–FR-7.10
**NFRs:** NFR-4, NFR-5, NFR-8
**UX-DRs:** UX-DR16
**Party-mode finding applied:** SSE auth seam (httpOnly cookie, NOT URL/query-param token) is explicit AC in S6.2

### Epic 7: Proactive Insights (committed must-ship)
A user receives named behavioral patterns with specific evidence blocks, honest framing, and the ability to dismiss irrelevant insights — so they understand their money without being lectured.
**FRs covered:** FR-8.1–FR-8.6
**NFRs:** NFR-1 (SEBI phrasing), NFR-4
**UX-DRs:** UX-DR7, UX-DR8

### Epic 8: Hardening, Edge Cases & Demo Readiness
Every edge case fails honestly. The IDOR cross-user isolation test passes. The full demo loop completes end-to-end without surprises.
**FRs covered:** NFR-1 hardening across all prior epics; FR-1.4 IDOR test completion
**NFRs:** NFR-1, NFR-2, NFR-8
**UX-DRs:** UX-DR7 (all edge-state copy)
**Party-mode finding applied:** Dedicated IDOR story added — asserts user A cannot read user B's transactions, commitments, or chat history (spans data from Epics 2, 5, 6)

---

## Epic 1: Secure Access & App Foundation

A user can register, log in, and securely access the application with data scoped to them alone. The project skeleton is live and runnable with all shared utilities in place.

### Story 1.1: Project Skeleton & App Scaffold

As a developer,
I want a running Reflex app with the correct project structure, pinned dependencies, and validated assumptions,
So that every subsequent story has a consistent foundation and no surprises on Day 1.

**Acceptance Criteria:**

**Given** a fresh clone of the repo
**When** `reflex run` is executed
**Then** the app serves a blank multi-page app locally with no errors
**And** the directory structure matches the architecture spine: `finance_app/pages/`, `finance_app/components/`, `finance_app/state/`, `finance_app/models.py`, `services/{ingestion,categorize,engine,narrate,utils}/`, `tests/`, `data/`, `.env.example`, `requirements.txt`
**And** Reflex and reflex-local-auth versions are pinned in `requirements.txt`
**And** `statementsparser` is validated to cover the HDFC demo bank format (Day 1, Hour 1 — flagged assumption; if it fails, document the gap immediately)
**And** `.env` is git-ignored; `.env.example` contains `ANTHROPIC_API_KEY=` as a placeholder
**And** no file under `services/` imports `reflex` or any `rx.*` namespace (verified by `grep -r "import reflex" services/` returning empty)

### Story 1.2: Database Schema & Shared Formatting Utilities

As a developer,
I want all database tables created and shared currency/date formatting utilities in place,
So that every subsequent story can persist data and display numbers consistently without reinventing formatting.

**Acceptance Criteria:**

**Given** docker-compose is available (with `docker-compose.yml` defining the `postgres:16-alpine` service `db`) and `DATABASE_URL` defaults to the local Postgres DSN when unset (`rxconfig.py` / `alembic/env.py`)
**When** `docker-compose up -d db` starts PostgreSQL 16 and `alembic upgrade head` is run
**Then** the PostgreSQL database is provisioned with all 8 tables: `users`, `uploaded_files`, `transactions`, `merchant_rules`, `commitments`, `score_events`, `insights`, `chat_messages` (SQLite is used only by throwaway unit-test engines, never as the app store)
**And** each user-scoped table has an integer primary key and a `user_id` foreign key
**And** `direction` enum is `credit`|`debit`; `category_source` is `rule`|`llm`|`user`; `criticality` is `critical`|`important`|`flexible` with default `important`
**And** `services/utils/format.py` exports `formatINR(amount: float) -> str` using Indian number grouping (e.g. `₹1,25,000` for 125000.0)
**And** `services/utils/format.py` exports `formatDate(iso: str) -> str` returning `"30 Jun 2026"` for `"2026-06-30"`
**And** `pytest tests/utils/` passes with edge cases: zero (₹0), crore amounts (₹1,00,00,000), leap-year dates, and invalid input raises `ValueError`
**And** all arithmetic in `services/` uses `Decimal`, never `float` (format functions accept float for display only)

### Story 1.3: User Registration

As a new user,
I want to register with email and password and then log in,
So that I can create my account securely and start uploading my statement.

**Acceptance Criteria:**

**Given** I am on the registration page
**When** I fill in a valid email and password and submit
**Then** my account is created with a bcrypt-hashed password (never stored plaintext)
**And** no session is created and there is no auto-login/auto-redirect — the form is replaced by a `"Registration successful → Return to Login"` confirmation panel (`role="status"`, `aria-live="assertive"`) directing me to log in (product decision 2026-07-09, supersedes the original auto-login intent)
**And** because registration creates no session, no auth token is written anywhere; the httpOnly/SameSite cookie rule (never localStorage, sessionStorage, or a custom header) applies when I subsequently log in (Story 1.4)
**And** the page displays `"No guessing. No shame."` above the form fields — removing this text fails acceptance
**And** the password field includes a show/hide toggle
**And** T&C and Privacy links open in an in-page modal, not a new tab
**And** no consent checkbox is pre-ticked (DPDP Rule 4)

**Given** I submit with an already-registered email
**When** the error renders
**Then** the message includes an inline `"Log in instead?"` link

### Story 1.4: User Login, Logout & Protected Routes

As a returning user,
I want to log in securely and have all protected pages redirect unauthenticated access,
So that my data is protected and I can always get back to where I need to be.

**Acceptance Criteria:**

**Given** I have a registered account and submit valid credentials
**When** the form is submitted
**Then** I am authenticated and redirected to the Dashboard (or Upload if no statement uploaded)
**And** the session token is set as an httpOnly, SameSite cookie

**Given** I am logged in
**When** I click logout
**Then** my session cookie is cleared and I am redirected to the login page

**Given** I attempt to navigate to any protected page (Upload, Transactions, Dashboard, Insights, Copilot) while unauthenticated
**When** the page loads
**Then** I am redirected to the login page

**Given** two registered users (User A and User B) with separate accounts
**When** User A is logged in and a direct DB query is filtered only by User B's `user_id`
**Then** it returns empty results for User A's session (IDOR baseline)

### Story 1.5: Auth Confirmation UX, Validation Behavior & Nav Scaffold

As a user registering or logging in,
I want inline validation feedback, an accessible registration-success confirmation, and a persistent navigation skeleton,
So that I can complete auth confidently and the nav is in place for all subsequent screens.

**Acceptance Criteria:**

**Given** I am on the registration or login form
**When** I leave any field (blur event)
**Then** validation fires immediately — on-submit-only validation is not acceptable
**And** error messages clear as I start typing (on input)

**Given** registration succeeds
**When** the success confirmation panel appears (replacing the form)
**Then** the panel is `role="status"` with `aria-live="assertive"` on the `"Registration successful!"` headline
**And** it offers a `"Return to Login"` action and creates no session — there is no auto-login and no auto-redirect (product decision 2026-07-09)

**Given** any of the 4 app screens renders (Transactions, Dashboard, Insights, Copilot)
**When** the page loads
**Then** a persistent left sidebar navigation (~200px) is visible with links to all 4 screens — even as a skeleton with placeholder routes for screens not yet built

---

## Epic 2: Statement Upload & Transaction Extraction

A user can upload their bank statement (PDF or CSV) and see a clean, de-duplicated list of transactions with honest progress feedback and honest refusal for unsupported formats.

### Story 2.1: Canonical Transaction Schema & Parser Protocol

As a developer,
I want a single canonical transaction shape and a `StatementParser` protocol that all parsers must implement,
So that every parser returns the same structure and downstream services never fork on source format.

**Acceptance Criteria:**

**Given** `services/ingestion/` exists
**When** any parser (CSV or PDF) returns its result
**Then** it returns a list of objects conforming to the canonical `Transaction` schema: `id, user_id, source_file_id, date, description_raw, merchant_normalized, amount, direction (credit|debit), balance_after, category, category_source, category_confidence, created_at`
**And** no parser-specific shape crosses the `services/ingestion/` boundary
**And** the `StatementParser` protocol is defined as a Python `Protocol` class with a single `parse(file_path: Path) -> list[Transaction]` method
**And** `pytest tests/ingestion/` passes with a stub parser that implements the protocol

### Story 2.2: CSV Parser — Indian Bank Formats

As a user with a CSV bank statement,
I want to upload it and have it parsed correctly into transactions,
So that I can see my data without manually reformatting anything.

**Acceptance Criteria:**

**Given** I upload a valid CSV bank statement in any of ≥2 supported Indian bank column shapes (e.g. HDFC, SBI)
**When** parsing completes
**Then** all transactions have correct dates (ISO-normalized), amounts (`Decimal`), and `direction` (`credit` or `debit`) — no float arithmetic on amounts
**And** the dedup key `(user_id, date, amount, description_raw, balance_after)` is normalized before comparison: ISO date, trimmed/whitespace-collapsed `description_raw`, `abs(amount)` — a re-upload of the same file creates zero duplicate rows
**And** `pytest tests/ingestion/test_csv_parser.py` passes with a golden-file fixture for each supported bank shape

### Story 2.3: PDF Parser Chain — Text-Based Statements

As a user with a PDF bank statement,
I want to upload it and have it parsed correctly,
So that I don't have to export a CSV manually.

**Acceptance Criteria:**

**Given** I upload a text-based (non-scanned) PDF bank statement
**When** parsing completes
**Then** the parser chain runs: statementsparser → pdfplumber → camelot fallback (each attempted in order; next tried only if previous yields no rows)
**And** transactions have correct counts, dates, amounts, and direction matching the source
**And** the demo fixture `data/demo-data.json` (24 transactions, June 2026 HDFC) parses to exactly 24 rows with correct values
**And** `pytest tests/ingestion/test_pdf_parser.py` passes with the HDFC golden-file fixture

**Given** I upload a scanned/image PDF (no text layer)
**When** the parser attempts extraction
**Then** a typed `IngestionError` is raised with message `"I can't read this one — it's a scanned image, not text. Try your bank's CSV export."` — not a crash, not wrong data, not a generic error toast

### Story 2.4: Upload Page — Progress, Summary & CTA

As a user uploading my statement,
I want to see honest progress steps and a real completion summary,
So that I know exactly what happened to my data.

**Acceptance Criteria:**

**Given** the upload page loads
**When** I view the page
**Then** a `"Step 1 of 3"` indicator (Upload → Review → Dashboard) is visible — functional onboarding contract, not decoration
**And** WebSocket availability in Reflex is validated first: if unavailable, 1-second polling is used for progress events (this validation must happen before writing the progress UI)

**Given** I select a file and begin upload
**When** parsing is in progress
**Then** the `"Review transactions"` CTA button is `aria-disabled` (not `hidden`, not `disabled`) — it remains keyboard-focusable
**And** 4 named real-server-state progress steps fire in sequence: `"Reading PDF"` → `"Identifying Transactions"` → `"Categorising by Rules"` → `"AI Assist"` — steps 3 and 4 are skeleton events in this story; they are completed with real data in Epic 3 (S3.1, S3.2)
**And** progress events are delivered via WebSocket push (or 1-second polling fallback)

**Definition of Done:** Steps 3–4 firing as skeleton/placeholder events is sufficient to mark **this story** done. Epic 2 as a whole is not done until S3.1 and S3.2 land and steps 3–4 carry real categorization data — do not treat Epic 2's completion as blocking on Epic 3, but do not report the upload flow as fully honest/real until both are merged.

**Given** parsing completes successfully
**When** the completion summary renders
**Then** it shows `"{n} categorized by rules · {n} by AI · {n} need your help"` derived from real parse output — not placeholder text
**And** for the demo fixture (24 transactions), the split is derived from whichever Tier-1 rules engine is live at the time — this was originally estimated as `"18 categorized by rules · 3 by AI · 3 need your help"`, but the Tier-1 engine actually built in Story 3.1 (a broader, ~90-rule India-merchant table that landed ahead of that story and was kept as-is, then extended by 2 rules during that story's code review — see 3-1 story's Change Log) rule-matches **all 24 of 24** rows on its own, leaving nothing for Tier-2/needs-review on this fixture. The literal numbers here are illustrative, not a fixed contract — the AC's requirement is that the three counts are always derived from real parse output, whatever they are. A future demo fixture revision (or a real user statement) is what will actually exercise the `by AI` / `need your help` counts once Story 3.2 lands.
**And** the `"Review transactions"` CTA becomes active (aria-disabled removed)

**Given** I navigate back during an in-progress upload
**When** the back navigation fires
**Then** a confirmation prompt appears before leaving the page

**Given** a parse failure occurs
**When** the error renders
**Then** empathetic copy appears (not a generic error toast) plus a contact/support link
**And** the typed `IngestionError` is caught by the `rx.State` handler and translated to plain-language user copy — never re-raised as a generic `Exception` to the UI

### Story 2.5: Deduplication & Persistence

As a user who re-uploads a statement or uploads a wider date range,
I want the app to never create duplicate transactions,
So that my counts and calculations are always accurate.

**Acceptance Criteria:**

**Given** I upload a statement that overlaps with a previously uploaded one
**When** the ingestion pipeline runs
**Then** each transaction is deduped on the canonical key `(user_id, date, amount, description_raw, balance_after)` before insert
**And** key components are normalized before comparison: date to ISO format, `description_raw` trimmed and whitespace-collapsed, `amount` as `abs(Decimal)`
**And** re-uploading the exact same file results in zero new rows
**And** uploading a wider date range inserts only the genuinely new transactions
**And** `pytest tests/ingestion/test_dedup.py` covers overlapping upload, exact re-upload, and wider-range upload scenarios

---

## Epic 3: Transaction Categorization & Teach Me

A user sees every transaction categorized with provenance badges and can teach the app to correct mistakes, with corrections persisting across future uploads.

### Story 3.1: Tier-1 Rules Engine & Transactions Table

As a user who just uploaded a statement,
I want to see all my transactions instantly categorized by recognizable merchant/keyword rules with a clean table view,
So that the bulk of my data is ready to review without waiting for AI.

**Acceptance Criteria:**

**Given** a parsed statement has been ingested
**When** the Tier-1 rules engine runs
**Then** ≥40 India-relevant merchant/keyword rules are applied (e.g. Swiggy→Dining, Netflix→Entertainment, EMI/HDFC→Loan Repayment)
**And** matched transactions have `category_source='rule'` and `category_confidence=1.0`
**And** the upload progress bar step 3 (`"Categorising by Rules"`) fires with a real row count when this step completes — completing the skeleton wired in Epic 2 Story 2.4
**And** the transactions page renders a table with all transactions: date, merchant, amount, direction, category, badge
**And** credit/income rows have a visually distinct green treatment (UX-DR14)
**And** filter chips are dynamically generated from actual parsed categories; a `"Needs review"` chip is always present when uncategorized count > 0
**And** `"Needs review"` banner uses amber tone, not error red
**And** the `"See my Dashboard"` CTA is always visible and enabled (sticky) — user is never blocked in the review loop
**And** `pytest tests/categorize/test_rules.py` passes asserting the demo fixture's 18 rule-matched transactions

### Story 3.2: Tier-2 LLM Categorizer (Claude Haiku)

As a user with uncategorized transactions,
I want the app to automatically categorize them using AI with a constrained category set,
So that I don't have to manually label every transaction the rules didn't recognize.

**Acceptance Criteria:**

**Given** transactions remain uncategorized after Tier-1 rules
**When** the Tier-2 LLM categorizer runs
**Then** it calls `claude-haiku-4-5` via `messages.parse()` with a Pydantic model whose `category` field is a `Literal` enum defined in `services/categorize/schema.py` — free-text categories from the LLM are structurally impossible
**And** each result stores `category_source='llm'`, `category_confidence` (float, never shown raw to user), and `reasoning`
**And** the enum hard-constraint also prevents prompt injection: a hostile merchant string like `"IGNORE PREVIOUS INSTRUCTIONS"` cannot produce an invented category
**And** the upload progress bar step 4 (`"AI Assist"`) fires with a real count when this step completes — completing the skeleton from Epic 2
**And** LLM calls are made via a `Categorizer` interface (not direct SDK calls) — mockable for unit tests
**And** `pytest tests/categorize/test_llm_categorizer.py` passes with all LLM calls mocked; no real API call is made during tests
**And** for the demo fixture: the 3 AI-categorized transactions receive correct categories with `category_source='llm'`

### Story 3.3: "Teach Me" — User Correction & Merchant Rules

As a user who sees a miscategorized transaction,
I want to correct it and have that correction apply to all matching merchants now and in future uploads,
So that the app gets smarter with my specific spending patterns.

**Acceptance Criteria:**

**Given** I click a transaction's category badge to correct it
**When** I select the correct category and confirm
**Then** a `merchant_rules` row is written: `(user_id, pattern, category, source='user')`
**And** a `"Re-apply to all matching merchants"` toggle is shown, defaulting ON
**And** when the toggle is ON, all transactions matching the merchant pattern in the current statement are updated to `category_source='user'`
**And** the confirmation reads `"Got it — I'll call [Merchant] '[Category]' from now on."` — not `"Category updated successfully."`
**And** on the next upload, the merchant rule is applied automatically via the Tier-1 rules engine (user rules checked before system rules)
**And** `pytest tests/categorize/test_teach_me.py` passes: correction persists, re-apply updates matching rows, future upload picks up the rule

### Story 3.4: Confidence Badges & Transaction Table Polish

As a user reviewing my transactions,
I want to clearly see which transactions were categorized by rules, by AI, or need my review — without being shown raw confidence percentages,
So that I understand the quality of categorization at a glance.

**Acceptance Criteria:**

**Given** the transactions table renders
**When** each row displays its category
**Then** `category_source='needs_review'` (confidence below threshold) → amber `"?"` badge
**And** `category_source='llm'` → blue `"AI"` badge
**And** `category_source='rule'` or `category_source='user'` → no badge
**And** raw confidence percentages are never shown anywhere in the UI
**And** the transaction list uses virtual scroll — standard DOM list is not acceptable for 100–300 rows
**And** virtual scroll renders without layout thrash at 300 rows on a standard developer machine
**And** the `"Needs review"` count in the filter chip matches the actual count of badge-carrying transactions

---

## Epic 4: Financial Engine — Safe-to-Spend & Confidence Score

The deterministic engine computes Safe-to-Spend and Confidence Score with a full pytest suite passing across all 13 scenarios. No LLM touches these numbers. This is the product's honesty spine and non-negotiable quality gate.

⚠️ **HIGH-RISK EPIC** — Largest epic by FR count. If bleeding into Day-3 morning, invoke scope-guard cut order immediately. `pytest tests/engine/` green is the gate before Epic 5 is wired.

**Developer note:** This epic has **no user-visible output of its own** — `services/engine/` is a pure backend module with no UI. Its only observable artifact is a green `pytest tests/engine/` run. Don't expect anything to look different in the app after finishing Epic 4; the payoff shows up in Epic 5 when the Dashboard wires to it.

### Story 4.1: Engine Pre-Flight — Read & Lock the Scenario Contract

As a developer,
I want to fully read and internalize the scenario spec before writing a single line of engine code,
So that the implementation targets the exact contract the pytest suite will assert.

**Acceptance Criteria:**

**Given** `_bmad-output/planning-artifacts/safe-to-spend-scenarios.md` exists
**When** this story is complete
**Then** the developer has read all 13 scenarios (7 core + 3 boundary + scenario 11 over-conservatism guard + scenario 12 salary-not-detected + scenario 13 days=0 payday-is-today ÷0 guard) and documented the expected output for each evidence-pack field in a comment block at the top of `tests/engine/test_safe_to_spend.py`
**And** the Reservation Rule (DD-1) — four sub-rules for known/predicted/variable/income-day commitments — is understood and documented in `services/engine/safe_to_spend.py` as a docstring before any logic is written
**And** the buffer decision (DD-2, default ₹2,000) is confirmed
**And** this story is marked done before S4.2 begins — no engine code before the contract is locked

### Story 4.2: Safe-to-Spend Engine Implementation

As the system,
I want a deterministic STS engine that produces a two-layer spend figure and full evidence pack,
So that the dashboard can display an honest, traceable Safe-to-Spend that never causes a missed commitment.

**Acceptance Criteria:**

**Given** `services/engine/safe_to_spend.py` is implemented
**When** the engine is called with a user's transactions, commitments, and buffer
**Then** it implements the formula: `safe_to_spend_today = max(0, (available_balance − reserved_total − buffer) ÷ days_until_next_confirmed_income)`
**And** `days_until_next_confirmed_income` is guarded before division: if 0 (payday is today) or undefined (no confirmed future income), the engine falls back to reserved-only mode and surfaces an `"add your payday"` prompt — never divides by zero, never returns `Infinity`
**And** STS is rounded **down** to the nearest ₹10 using `math.floor(x / 10) * 10` on a `Decimal` value — never rounded up
**And** STS is floored at `max(0, ...)` — never negative
**And** all arithmetic uses `Decimal` (or integer paise), never `float`
**And** the Reservation Rule (DD-1) is implemented in full: known commitments due on-or-before income always fully reserved; predicted commitments only inside criticality proximity window (7d Critical / 5d Important / 3d Flexible); variable-amount commitments reserve top-of-range; commitment due on income day reserved against current balance unless income confidence High AND income ≥ commitment
**And** the engine returns the full evidence pack struct: `{reserved_total, spendable_pool, days_to_income, safe_to_spend_today, safe_to_spend_after_income (nullable), prediction_confidence (Low|Medium|High), drivers[], data_quality_flags[], safety_ok}`
**And** `safety_ok = True` only when every commitment due on or before next confirmed income is fully covered by `reserved_total`
**And** no file in `services/engine/` imports from `reflex` or any `rx.*` namespace
**And** `services/engine/` has no import of `services/narrate/` — the hard boundary (AD-1) is enforced

### Story 4.3: Safe-to-Spend pytest Suite — All 13 Scenarios

As a developer,
I want a table-driven pytest suite asserting every field of the engine output across all 13 scenarios,
So that the honesty spine is machine-verified and no edge case can silently regress.

**Acceptance Criteria:**

**Given** `tests/engine/test_safe_to_spend.py` is implemented
**When** `pytest tests/engine/` is run
**Then** all 13 scenarios pass: 7 core + 3 boundary + scenario 11 (over-conservatism guard) + scenario 12 (salary-not-detected, `days` undefined) + scenario 13 (payday-is-today, `days=0`)
**And** the test fixture injects an LLM client that **raises on construction or use** — any accidental LLM call fails loudly, never silently passes
**And** every field of the evidence pack is asserted by name: `reserved_total`, `spendable_pool`, `days_to_income`, `safe_to_spend_today`, `safe_to_spend_after_income`, `prediction_confidence`, `safety_ok`
**And** `safety_ok` is `True` for scenarios 1–9, 11, 12, 13 and `False` with honest shortfall for scenario 10
**And** scenario 10 returns `safe_to_spend_today=Decimal('0')` with a shortfall message — not a negative value or crash
**And** scenario 11 returns a non-zero STS on a commitment-free, buffer-covered balance (over-conservatism guard)
**And** scenario 12 returns `safe_to_spend_after_income=None` plus `"no_income_detected"` in `data_quality_flags`
**And** scenario 13 (`days_until_next_confirmed_income=0`) returns `safe_to_spend_today=Decimal('18000')` via the reserved-only fallback — never a `ZeroDivisionError`, never `Infinity`/`NaN`; this and scenario 12 together are the full test of the ÷0 guard required by AC line above and by `project-context.md`'s Seams section
**And** all STS figures in passing scenarios end in `0` (₹1,250 not ₹1,254) — rounding verified by assertion
**And** `pytest services/engine/` runs in < 10 seconds with zero network calls

### Story 4.4: Confidence Score Engine & score_events Writeback

As the system,
I want a deterministic Confidence Score that writes an auditable event for every change,
So that every score the user sees is traceable to a specific financial event with a plain-language explanation.

**Acceptance Criteria:**

**Given** `services/engine/confidence_score.py` is implemented
**When** the engine computes or updates the score
**Then** the Confidence Score (0–100) measures financial preparedness only: commitment coverage, buffer health, spending pace vs. income, savings trend — never app engagement
**And** Prediction Confidence (Low/Medium/High) measures data completeness: statement recency, categorization coverage, commitment-detection certainty — never conflated with the Score
**And** cold-start: score is computed immediately on first upload; Prediction Confidence = Low or Medium with a stated reason; framed as `"Confidence grows with more data"` — no fake neutral-50, no failure state
**And** every score change atomically writes a `score_events` row: `score, delta, trigger_event, explanation, suggested_action, timestamp` — column name is `trigger_event` (not `triggering_event`), matching the data model exactly
**And** the score shown in the UI is derived from the latest `score_events` row — never from a bare score column
**And** no code path updates the score without writing a matching event row (score write is a single function that does both atomically)
**And** the CS-1 through CS-4 assertions from `safe-to-spend-scenarios.md` pass as part of `pytest tests/engine/`
**And** a ₹0 Safe-to-Spend never coexists with a "Well prepared" Confidence Score — the two must be consistent

---

## Epic 5: Dashboard, Briefing & Commitment Management

A user sees their Safe-to-Spend hero card, Confidence Score chip, morning briefing, and charts on a single calm screen — and can add/edit/delete commitments that immediately update the Safe-to-Spend figure.

### Story 5.1: Dashboard Layout — Hero Card & Confidence Chip

As a user who has uploaded a statement,
I want to open the Dashboard and immediately see my Safe-to-Spend and Confidence Score above everything else,
So that I get the answer to "how much can I spend?" before I see any charts.

**Acceptance Criteria:**

**Given** I navigate to the Dashboard after a statement has been parsed and the engine has run
**When** the page renders
**Then** the Safe-to-Spend hero card is the first visible element above the fold, before any chart
**And** the hero card displays: the `safe_to_spend_today` figure via `formatINR()`, one calm sentence explaining why, and the freshness caveat `"Based on your statement up to {formatDate(statement_end_date)}"` directly on the card — not in a footer
**And** the second STS layer `"After your salary on {date}: about {formatINR(safe_to_spend_after_income)}/day"` is a visually distinct row below — never merged into the hero figure
**And** if no salary is detected, the second layer reads `"We couldn't detect a salary — add one manually?"` — not a zero or error
**And** the Confidence Score chip displays a label only (`"Well prepared"` / `"On track"` / `"Watch this"`) — the raw score number is never rendered anywhere
**And** the `"Show me why"` drill-in link is present on the hero card (not `"View details"`)
**And** a `"Why?"` expandable block shows a 1–2 sentence explanation traceable to real engine data; fallback: `"We don't have enough data yet to fully explain this."`
**And** an amber stale-data banner appears above the hero card when `statement_end_date` is >30 days before today, prompting re-upload
**And** the dashboard initial render completes in < 3 seconds after parse
**And** all currency displays use `formatINR()`, all dates use `formatDate()` — no f-string formatting anywhere on this page

### Story 5.2: Confidence Score Drill-In Panel

As a user who wants to understand my Confidence Score,
I want to tap the chip and see exactly what moved it with every change traced to a real event,
So that I trust the number because I can see its history.

**Acceptance Criteria:**

**Given** I tap the Confidence Score chip
**When** the drill-in panel opens
**Then** it shows the Prediction Confidence label and reason (e.g. `"Medium — some cash spends may be missing"`)
**And** it lists `score_events` rows in reverse chronological order: `delta`, `explanation`, and time elapsed
**And** every row corresponds to a real `score_events` DB row — no unexplained changes are ever shown
**And** tapping the chip a second time collapses the panel
**And** the raw Confidence Score number is never shown — label only throughout

### Story 5.3: Morning Briefing Narration

As a user on the Dashboard,
I want to read a short, honest, plain-language briefing that explains my financial situation,
So that I understand my money in 2–4 sentences without jargon or judgment.

**Acceptance Criteria:**

**Given** the Dashboard loads and the engine evidence pack is available
**When** the briefing panel renders
**Then** it calls `services/narrate/` with the engine evidence pack and a prompt-cached system prompt (tone: honest, calm, non-judgmental)
**And** the briefing follows the Observation → Evidence → Explanation → Action structure
**And** every number in the briefing prose exactly equals the engine output — no rounding differences, no invented figures
**And** the LLM model used is `claude-opus-4-8` (or `claude-sonnet-5` as cost lever) — configured as a constant in `services/narrate/config.py`, never hardcoded at the call site
**And** the system prompt is marked `cache_control: {"type": "ephemeral"}`; volatile per-turn context is placed after the cache breakpoint
**And** `services/narrate/` does not import `services/engine/` — it receives the evidence pack as input only
**And** the briefing snapshot is fixed at generation time; the hero card figures are live — this divergence is intentional
**And** (FR-8.6) when at least one active, non-dismissed insight exists in the `insights` table, the briefing weaves in a reference to the single highest-priority one — sourced verbatim from that insight's `observation` field, never invented or recomputed by `services/narrate/` (AD-1: narrate emits only figures/text present in what it's handed). When no insight exists yet (e.g. first upload, insufficient data, or Epic 7 not yet run), the briefing simply omits the insight sentence — this is graceful degradation, not an error state

### Story 5.4: Dashboard Charts & Spending Breakdown

As a user who wants to explore their spending,
I want to see category and trend charts below the hero section,
So that I can understand where my money went as supporting evidence — not as the headline.

**Acceptance Criteria:**

**Given** the Dashboard hero section has rendered
**When** I scroll below the fold
**Then** `rx.plotly` charts are rendered: spending by category (donut/bar) and a monthly pace trend
**And** charts appear **below** the hero card and briefing — never above the fold
**And** chart axis labels, tick values, and tooltips use `formatINR()` and `formatDate()` — `rx.plotly` default number formatting is explicitly overridden (raw `125000.0` on chart labels fails acceptance)
**And** an upcoming commitments timeline is displayed showing commitment name, amount, due date, and criticality tier

### Story 5.5: Commitment Management Page — List, Add, Edit, Delete (screen 02.1)

As a user who wants to declare a recurring obligation,
I want a dedicated Commitments page to list, add, edit, and delete commitments and see my Safe-to-Spend impact,
So that my ring-fencing accurately reflects my real financial obligations.

**Acceptance Criteria:**

**Given** I click `"+ Add a commitment"` on the Dashboard
**When** it activates
**Then** I navigate to the dedicated **Commitments Management page** (WDS prototype screen `02.1`) — **not** an inline Dashboard modal (product decision: align to the WDS prototype)
**And** the page shows a Safe-to-Spend **impact bar**, and a list of my commitments (name, amount, due-day, criticality) each with a per-row **Edit / Delete** menu

**Given** I am on the Commitments page
**When** I open `"+ Add"` (or a row's Edit)
**Then** an add/edit **modal on this page** shows fields: name, amount, due-day (1–31), criticality (Critical / Important / Flexible) with default `Important`
**And** on save, the `rx.State` handler calls `services/engine/` — no inline STS arithmetic in the handler
**And** the engine result is written to DB, the page's Safe-to-Spend impact bar updates, and the Dashboard hero reflects the new figure when next rendered (never a stale number)
**And** `due_day=31` is stored as `31` and rendered as `"end of month"`; in months shorter than 31 days it resolves to the last calendar day
**And** edit and delete follow the same pattern: call engine → write result → yield UI update
**And** `POST /commitments` and `PATCH /commitments/{id}` responses include `safe_to_spend_updated`

### Story 5.6: Commitment Auto-Detection

As a user who hasn't manually declared their EMI or rent,
I want the app to proactively detect recurring charges and ask me to confirm them,
So that my commitments are ring-fenced without me having to remember to add them manually.

**Acceptance Criteria:**

**Given** a statement has been parsed with transactions
**When** the recurring-debit detector runs
**Then** it identifies transactions with similar amount (±10%) and ~monthly cadence
**And** each candidate is surfaced as a confirmation prompt: `"We noticed a ₹8,500 charge every 5th — is this an EMI?"`
**And** the user can confirm (creates a `commitments` row) or dismiss (suppresses future prompts for that pattern)
**And** confirmed commitments immediately feed Safe-to-Spend ring-fencing
**And** `pytest tests/engine/test_commitment_detector.py` covers: EMI-like pattern detected, irregular amounts not detected, dismissed pattern not re-surfaced

---

## Epic 6: AI Copilot (committed must-ship)

A user can ask natural-language questions about their finances and receive streamed, honest answers citing real data — never invented numbers — with full trace chips and graceful "I don't know" responses.

### Story 6.1: Copilot Chat UI with Streaming

As a user who wants to ask a financial question,
I want a chat interface where responses stream in token-by-token and my history is preserved,
So that the interaction feels live and I can refer back to previous answers.

**Acceptance Criteria:**

**Given** I navigate to the Copilot page
**When** the page loads
**Then** a chat input and thread are visible
**And** the chat thread element has `role="log"` and `aria-live="polite"` — screen readers announce completed sentences only, not every token
**And** the send button uses `aria-disabled` (not `disabled`) while a response is streaming

**Given** I type a question and submit
**When** the Copilot handler calls the Claude API
**Then** response tokens stream into the chat bubble token-by-token via an async `rx.State` handler that yields Claude's stream
**And** the streamed text is chunked at sentence boundaries for screen reader announcement
**And** the completed response is stored in `chat_messages` with `(user_id, role='assistant', content, trace_sources, timestamp)` — server-side, scoped to `user_id`, never in localStorage
**And** my prior messages in this session are visible when I return to the page

### Story 6.2: Read-Only Tools & Honesty Enforcement

As the system,
I want the Copilot to answer only from real data via read-only tools, never inventing figures or performing financial actions,
So that every number in a Copilot response is traceable to the deterministic engine or the user's actual transactions.

**Acceptance Criteria:**

**Given** the Copilot LLM is invoked
**When** it needs financial data to answer
**Then** it calls only these read-only tool implementations: `get_safe_to_spend`, `get_confidence_score`, `query_transactions`, `get_spending_by_category`, `get_upcoming_commitments`
**And** no write-capable function appears in the tool list
**And** each tool implementation queries the DB with an explicit `user_id` filter — no cross-user data leak
**And** the LLM system prompt includes four hardcoded, non-configurable rules: (1) Never invent or estimate financial figures — only cite values from tool results; (2) Express uncertainty explicitly when data is incomplete; (3) Never give investment recommendations (SEBI IA boundary); (4) Always populate the `trace` field citing data sources used
**And** the LLM model is `claude-opus-4-8` (or `claude-sonnet-5` as cost lever) — configured as a constant in `services/narrate/config.py`, never hardcoded at the call site
**And** the system prompt is marked `cache_control: {"type": "ephemeral"}`
**And** the `/copilot/chat` endpoint uses the httpOnly cookie for auth — the session token is **never** placed in the URL or as a query parameter (EventSource cannot send custom headers; the cookie is sent automatically — URL token placement leaks into server logs and is explicitly forbidden) (AD-5 × AD-11 seam guard)
**And** 10 scripted questions from `copilot_samples` in `demo-data.json` are answered with zero invented numbers

### Story 6.3: SSE Streaming Contract, Trace Chips & Error Resilience

As a user receiving a Copilot response,
I want to see data-source trace chips below each answer and have the stream always close cleanly even on errors,
So that I can verify where numbers came from and the UI never hangs.

**Acceptance Criteria:**

**Given** the Copilot stream is active
**When** the server emits events
**Then** exactly three SSE event types are emitted: `{ "type": "token", "text": "<string>" }`, `{ "type": "trace", "sources": [...] }`, `{ "type": "done" }`
**And** the `done` event is emitted from a `finally` block — it fires even if the LLM stream raises mid-token (the browser `EventSource` must never hang)
**And** if the LLM stream raises mid-token, an explicit error frame is emitted before `done` so the UI can show an honest error rather than silence
**And** the client ignores unknown SSE event types gracefully (forward compatibility)

**Given** the response contains data-cited figures
**When** the response bubble renders
**Then** `"Based on: …"` trace chips appear below the bubble — one per tool called
**And** tapping a trace chip navigates to the underlying data view

**Given** an out-of-scope or insufficient-data query (e.g. "Should I invest in gold?")
**When** the Copilot responds
**Then** it returns a graceful, honest response — never silence, never a hallucinated answer

### Story 6.4: Quick Prompts & Insights Context Handoff

As a user who wants a fast gut-check or to dig deeper from an Insight card,
I want pre-built quick prompts and seamless context handoff from Insights,
So that I can ask the most common questions without typing and continue an insight's thread naturally.

**Acceptance Criteria:**

**Given** I am on the Copilot page with no active conversation
**When** the page loads
**Then** quick-prompt buttons are visible (e.g. `"Can I afford ₹___ this weekend?"`, `"How am I doing?"`)
**And** tapping a quick prompt pre-fills the input and submits it
**And** `"Can I afford ₹X this weekend?"` reasons over the real Safe-to-Spend from the engine — never a hardcoded or invented figure

**Given** I tap `"Ask Copilot"` from an Insight card
**When** the Copilot page opens
**Then** the input is pre-populated with context from the insight
**And** a dismissable `"Talking about: {pattern name}"` chip is visible above the input
**And** the `insight_id` is included in the POST body sent to `/copilot/chat`

---

## Epic 7: Proactive Insights (committed must-ship)

A user sees pattern-based financial insights surfaced automatically — each narrated honestly in O→E→E→A shape, dismissable, and linkable to the Copilot for deeper conversation.

### Story 7.1: Insight Detector Engine — All 5 Patterns Coded

As the system,
I want all five insight detectors to run on post-upload and post-categorisation events so that the insight feed is always fresh without a manual refresh,
So that the user sees relevant observations without asking.

**Acceptance Criteria:**

**Given** the insight engine runs (triggered after every successful ingestion or categorisation batch)
**When** it evaluates the current user's transaction history
**Then** all five detectors execute in sequence, one class per FR-8.1 named pattern: `PostPaydaySpikeDetector` (post-payday spike), `DeathBySmallPurchasesDetector` (death-by-small-purchases), `ZombieSubscriptionDetector` (zombie subscriptions), `WeekendWeekdayPaceDetector` (weekend-vs-weekday pace), `UpcomingCommitmentCollisionDetector` (upcoming-commitment collision) — class names are 1:1 with FR-8.1's pattern list; no detector class exists without a named FR-8.1 pattern and vice versa
**And** each detector is a class implementing the `InsightDetector` protocol (method: `detect(user_id, db_session) → list[InsightCandidate]`)
**And** detectors live in `services/engine/insights/` — no Reflex imports
**And** `pytest services/engine/insights/` covers every detector with at least one true-positive and one true-negative fixture

**Given** the demo dataset is loaded
**When** the insight engine runs
**Then** at least 3 of the 5 detectors fire and produce at least one insight each — the demo is never a blank Insights page

### Story 7.2: Insight Narration — O→E→E→A Shape & SEBI Rule

As a user reading an insight,
I want each insight to be narrated in a specific, honest shape — Observation, Explanation, Effect, Advice — and to never cross into regulated investment advice,
So that I always understand what I'm looking at and why it matters, without the app overstepping.

**Acceptance Criteria:**

**Given** a detector produces an `InsightCandidate`
**When** `services/narrate/insight_narrator.py` generates the insight prose
**Then** the narration follows the four-part O→E→E→A structure exactly:
  - **O (Observation):** one sentence, present tense, states only what the data shows (e.g. "Your Swiggy spend jumped 40% this month.")
  - **E (Explanation):** one sentence, plain-language hypothesis (e.g. "This often tracks to a busier work schedule.")
  - **E (Effect):** one sentence, impact on STS or Confidence Score using values from the evidence pack only — never invented (e.g. "This shaved ₹12/day off your safe-to-spend.")
  - **A (Advice):** one sentence, always ends with a question that invites user reflection (e.g. "Want me to set a ₹1,500 dining cap?")
**And** the "Effect" sentence cites only figures already present in the engine evidence pack — no arithmetic in the narrator
**And** any insight touching investment, equity, mutual funds, or returns carries the SEBI phrasing rule: must end with "This is not investment advice." — enforced as a post-processor guard, not a per-narrator convention
**And** `pytest tests/narrate/test_insight_narrator.py` covers: correct shape, SEBI guard fires, SEBI guard does not fire for non-investment insights

### Story 7.3: Insights Page & Dismiss Lifecycle

As a user who has reviewed an insight,
I want to dismiss it so it doesn't clutter my feed, and have it resurface only if the underlying pattern materially changes,
So that my Insights page stays useful over time.

**Acceptance Criteria:**

**Given** I navigate to the Insights page
**When** the page loads
**Then** a dedicated Insights page is shown — separate from the Dashboard; reachable from the persistent left nav
**And** each insight card shows: pattern name (title), O→E→E→A prose, a "Dismiss" button, and an "Ask Copilot" button
**And** insights are ordered newest-first within severity tier (critical → important → flexible)
**And** (FR-8.5) when `data_months < 3` (fewer than 3 months of statement history), a footer note reads exactly: `"More data sharpens these patterns."` — hidden once 3+ months of history exist

**Given** I tap "Dismiss" on an insight
**When** the dismiss action processes
**Then** the insight is marked `dismissed=True` in the `insights` table with a `dismissed_at` timestamp
**And** the card is removed from the feed immediately (optimistic UI update via `rx.State`)
**And** the detector will not re-surface the same pattern for the same user unless the underlying metric changes by ≥15% (the "materially changed" threshold is a constant in `services/engine/insights/config.py`)

**Given** a dismissed insight's underlying pattern changes materially (≥15%)
**When** the detector runs next
**Then** a new insight row is created (the old dismissed row is not un-dismissed — each surfacing is a new row)
**And** the new insight appears in the feed

**Given** I tap "Ask Copilot" on an insight card
**When** the Copilot page opens (story 6.4 handoff)
**Then** the `insight_id` is in the POST body and the "Talking about: {pattern name}" chip is visible

### Story 7.4: Dashboard Insight Teaser

As a user on the Dashboard,
I want to see a brief preview of my top insight without navigating away,
So that I notice actionable patterns at a glance.

**Acceptance Criteria:**

**Given** at least one active (non-dismissed) insight exists
**When** the Dashboard renders
**Then** the top insight is shown as a teaser card below the narration panel: pattern name, the Observation sentence only, and a "See all insights →" link
**And** the teaser is absent when no active insights exist (empty state: hidden, not "No insights" placeholder — per UX-DR-4, the hero card already fills the screen)

**Given** I tap the teaser card
**When** navigation fires
**Then** I land on the Insights page (story 7.3) scrolled to that specific insight

---

## Epic 8: Hardening & Demo-Readiness (committed must-ship)

The application handles all edge cases honestly, presents welcoming empty states, passes the IDOR security test, and can be demoed end-to-end without surprises. The README enables a fresh-machine setup in one command.

### Story 8.1: Edge-Case Honest Refusals

As the system handling unexpected or degenerate inputs,
I want every failure mode to surface an honest, plain-language message — never a raw exception, never a silently wrong result,
So that the app's honesty promise holds under adversarial conditions.

**Acceptance Criteria:**

**Given** a user uploads an empty PDF (zero bytes or zero parsed transactions)
**When** ingestion processes it
**Then** the typed `IngestionError` is raised with code `EMPTY_STATEMENT`
**And** the UI shows: "This file didn't contain any transactions I could read. Try your bank's CSV export or a different date range." (approved UX copy)
**And** no partial or empty transaction table is persisted

**Given** a user uploads a scanned-image PDF (no text layer)
**When** pdfplumber returns zero text
**Then** the typed `IngestionError` is raised with code `NO_TEXT_LAYER`
**And** the UI shows: "I can't read this one — it's a scanned image, not text. Try your bank's CSV export." (approved UX copy from ux-spec-mvp.md)

**Given** no confirmed future income row exists in `income_sources`
**When** the STS engine runs
**Then** STS does not divide by zero — it falls back to the reserved-only safe state
**And** the Dashboard hero card shows: "Upload your payday date so I can calculate your daily safe-to-spend."
**And** `pytest tests/engine/test_sts.py` scenario 12 (salary-not-detected) passes

**Given** a user has uploaded a valid statement but the LLM categorisation tier-2 call fails (network error, rate limit)
**When** categorisation falls back to rules-only
**Then** the `category_source` for affected rows is `rule` (not `llm`)
**And** the UI shows a dismissable caveat: "AI categorisation was unavailable — some categories may need your review."
**And** no uncategorised rows are silently left with a null category

**And** `pytest tests/ingestion/` covers all four scenarios above

### Story 8.2: Onboarding Empty States

As a first-time user with no data uploaded,
I want every screen to show a welcoming, action-directing empty state rather than a blank page or "No data available",
So that I know exactly what to do next.

**Acceptance Criteria:**

**Given** I have just registered and land on the Dashboard
**When** no statement has been uploaded
**Then** the hero area shows: "Upload a statement and I'll show you what's safe to spend — and why." with a prominent "Upload your statement" CTA button (approved UX copy)
**And** no charts, no STS number, no narration panel are rendered
**And** the Upload page step indicator ("Step 1 of 3") is visible as a visual hint

**Given** I navigate to the Transactions page with no data
**When** the page renders
**Then** the page shows: "Your transactions will appear here after you upload a statement." with a "Upload your statement" link

**Given** I navigate to the Insights page with no data
**When** the page renders
**Then** the page shows: "Insights will appear once I've analysed your statement." with a "Upload your statement" link

**Given** I navigate to the Copilot page with no data
**When** the page renders
**Then** the Copilot is still functional — I can ask questions — but quick prompts are hidden until data exists
**And** the first response to any question without data says: "I don't have your transactions yet. Upload a statement and I'll be able to give you real answers."

### Story 8.3: IDOR Security Test (Cross-User Data Isolation)

As the security baseline,
I want a dedicated automated test that asserts user A cannot access user B's data under any query path,
So that the Phase 1 single-user app is provably safe to extend to multi-user in Phase 2.

**Acceptance Criteria:**

**Given** two users (user A and user B) exist in the test DB with non-overlapping transactions, commitments, and chat history
**When** all service-layer query functions are called with `user_id = A`
**Then** zero rows belonging to `user_id = B` are returned — for every user-scoped table: `transactions`, `commitments`, `income_sources`, `score_events`, `insights`, `chat_messages`, `merchant_rules`

**Given** the same test scenario
**When** all aggregate/join queries are called (STS calculation, Confidence Score, spending-by-category, upcoming commitments)
**Then** every aggregate reflects only user A's data — no bleed from user B

**And** the test file is `tests/security/test_idor.py`
**And** it uses two real DB sessions (no mocks for the queries under test) on an in-memory SQLite instance
**And** `pytest tests/security/test_idor.py` must pass before any Phase 2 work begins — this is a gate, not a nice-to-have

### Story 8.4: README & One-Command Setup

As a developer (or the demo presenter) setting up the app on a fresh machine,
I want a single command to install, seed demo data, and launch the app,
So that the demo can be reset and rerun without a setup guide.

**Acceptance Criteria:**

**Given** a machine with Python 3.11+ and the repo cloned
**When** I run `make demo` (or `./scripts/demo_setup.sh`)
**Then** dependencies install from `requirements.txt` (pinned versions)
**And** `.env` is created from `.env.example` with a prompt for `ANTHROPIC_API_KEY` if not already set
**And** `demo-data.json` is loaded — all demo transactions, commitments, income source, and confidence-score events seeded for the canonical demo user
**And** the Reflex app starts at `localhost:3000`
**And** the entire sequence completes in under 3 minutes on a clean machine (not counting pip download time)

**Given** the README.md at the project root
**When** read by a developer
**Then** it contains: prerequisites, one-command setup, how to run tests (`pytest services/engine/`), how to reset demo data, and the architecture decision log pointer (`ARCHITECTURE-SPINE.md`)
**And** it does not contain any placeholder text or `TODO` lines

### Story 8.5: Demo Dry Run & Regression Guard

As the demo presenter,
I want a scripted walkthrough that verifies the golden path is intact and produces no surprises,
So that the demo is repeatable and trustworthy.

**Acceptance Criteria:**

**Given** the demo dataset is loaded (story 8.4 seed)
**When** the golden-path walkthrough executes: Register → Login → Upload HDFC demo statement → Review transactions → View Dashboard → View Insights → Ask Copilot "Can I afford ₹3,000 this weekend?"
**Then** each step completes without an unhandled exception or blank screen
**And** the Dashboard hero shows a non-zero STS figure with a one-sentence "why"
**And** at least 3 insight cards are visible on the Insights page
**And** the Copilot response cites the real STS figure (not an invented number) and streams without hanging
**And** the HDFC demo PDF parses to ≥90% of its known transaction count (golden-file regression)

**And** a `scripts/demo_dry_run.py` script exists that automates steps 3–7 using the Reflex test client and asserts the above outcomes
**And** `pytest scripts/demo_dry_run.py` is the final gate before declaring the MVP done
