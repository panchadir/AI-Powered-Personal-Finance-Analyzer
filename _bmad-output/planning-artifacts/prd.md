---
title: "AI-Powered Personal Finance Analyzer — Phase 1 MVP PRD"
status: final
created: 2026-07-08
updated: 2026-07-08
---

# PRD: AI-Powered Personal Finance Analyzer — Phase 1 MVP

**Created:** 2026-07-08
**Updated:** 2026-07-08
**Author:** ALPHA
**Status:** Final
**Type:** Lean MVP PRD

> **Sources of record:** strategic foundation from [`A-Product-Brief/project-brief.md`](A-Product-Brief/project-brief.md) and [`B-Trigger-Map/`](B-Trigger-Map/); technical architecture from [`planning-artifacts/research/technical-ai-financial-copilot-mvp-technical-architecture-stack-research-2026-07-07.md`](planning-artifacts/research/technical-ai-financial-copilot-mvp-technical-architecture-stack-research-2026-07-07.md); Safe-to-Spend/Confidence-Score design from [`problem-solution-2026-07-07.md`](problem-solution-2026-07-07.md) §3 Design Decisions DD-1/DD-2; engine test suite from [`planning-artifacts/safe-to-spend-scenarios.md`](safe-to-spend-scenarios.md); UX page specs from [`C-UX-Scenarios/`](C-UX-Scenarios/); UX layout hierarchy, microcopy, and enforcement from [`planning-artifacts/ux-spec-mvp.md`](ux-spec-mvp.md); prototype decisions from [`prototypes/01-priyas-first-honest-morning-Prototype/HANDOFF.md`](../../prototypes/01-priyas-first-honest-morning-Prototype/HANDOFF.md). This PRD does **not** restate those — it turns them into buildable requirements.

---

## 1. Overview & Goal

**Product job-to-be-done:** turn financial confusion into financial confidence for a financially-capable-but-overwhelmed salaried user — by showing them, from their own bank statement, how much they can safely spend, how prepared they are, and why, in plain language they trust.

**Strategic thesis:** the real competitor is not another finance app — it is *avoidance*. The product wins by being the thing that feels better than looking away. **Honesty is the structural moat:** every number is traceable, every recommendation carries visible uncertainty, and incumbents whose brand is "always right" cannot copy this without breaking their own positioning.

**Phase 1 MVP goal:** prove the core experience locally, end-to-end, in a **3-day build**. A user uploads a bank statement and leaves the app more informed and more confident about their money than when they opened it — with every number honestly explained and never overstated.

**The one thing that must be true:** every displayed number is traceable (source data → deterministic engine → evidence pack → plain-language narration), and the app never states a spend figure that would cause the user to miss a committed obligation.

**Kill-signal protocol:** if a Safe-to-Spend error causes a user to miss a real committed obligation, the feature pauses immediately and a trust audit runs before relaunch. This is not a post-launch decision — it is the operational stance of the honesty spine, built in from Day 1.

---

## 2. Scope

### In scope (the 9 MVP capabilities)
A successful Phase 1 MVP lets a user:
1. Sign up and securely access the application.
2. Upload a bank statement (PDF/CSV).
3. Have transactions automatically extracted and categorized.
4. View a clean financial dashboard with charts and summaries.
5. Receive a **Safe-to-Spend** recommendation with a clear explanation.
6. See a **Confidence Score** and understand what influenced it.
7. Ask natural-language financial questions through the AI Copilot.
8. Receive personalized insights and proactive financial guidance.
9. Leave the application feeling more informed and confident than when they opened it.

### MVP scope: the committed golden path
The **final MVP flow** is a single committed golden path — **Register → (auto) Login → Upload Statement → Transactions Table → Dashboard → AI Insights & Recommendations → AI Copilot** (capabilities 1–8; capability 9 = the informed-and-confident outcome). All seven steps are must-ship. **Delivery-risk note:** committing all eight capabilities in a 3-day solo build removes any stretch safety-margin; if the schedule slips, trim via the epics' scope-guard cut order (polish/quality first — the deterministic engine + honesty spine is never cut), do not silently drop a committed capability.

### Out of scope (deferred, not dropped)
Account Aggregator / FIU integration · WhatsApp delivery · DPDP consent-manager architecture · native mobile app · cloud deployment · multi-account reconciliation · scanned/image-PDF OCR · vernacular statement parsing at scale · real-time bank sync · email verification on register. The MVP runs **locally, single-user**, on uploaded statements only.

---

## 3. Target User & Primary User Journey

**Primary persona — "Priya":** salaried, Tier-1/2 India, ~32, fixed monthly income (~₹30k–₹2L/month), EMI-carrying, financially capable but emotionally overwhelmed. Avoids her banking app out of dread. Tried a budgeting app once and quit within days. Wants guidance, not homework.

**MVP data assumption:** predictable salaried income with an identifiable recurring credit. Irregular-income users are explicitly out of Phase 1 scope.

### Primary User Journey — "Priya's First Honest Morning"

> Purpose: give engineers the protagonist context that drives every UX and AC decision in this PRD. Full page-level detail is in [`C-UX-Scenarios/01-priyas-first-honest-morning/`](C-UX-Scenarios/01-priyas-first-honest-morning/).

**Evening — Priya hears about the app from a colleague.** She is anxious about an upcoming rent payment and an EMI she can't clearly remember. She opens the app.

1. **Register:** She sees "No guessing. No shame." above the form. She enters her email and password. The app creates her account and redirects her directly to Upload — no email gate.
2. **Auto-login transition:** A brief confirmation screen ("You're in — let's look at your money") auto-redirects to Upload within 3 seconds.
3. **Upload:** She uploads last month's HDFC statement (PDF). She watches four honest progress steps fire in sequence. The app summarizes: "18 categorized by rules · 3 by AI · 3 need your help." She reviews and corrects two merchants with Teach Me.
4. **Transactions table:** She sees a clean list. Green credits, debit rows, confidence badges. She clicks "See my Dashboard."

**Next morning — Priya opens the app again.**

5. **Dashboard:** The hero card leads with "Today: ₹1,250/day · After salary on 1 Aug: ₹990/day." Below it, a Confidence Score chip shows "Medium — Confidence grows with more data." She taps "Why?" and reads a two-sentence plain-language explanation. She reads the morning briefing narration. She feels calmer.
6. **AI Insights:** She sees three pattern cards. The first: "Post-payday spike — your spending jumps 40% in the 3 days after salary." Evidence block shows three specific transactions with amounts and dates. The Action line says "You might consider setting a soft daily limit for the first week of the month." She dismisses one irrelevant card.
7. **AI Copilot:** She taps the "Can I afford a ₹3,000 dinner this weekend?" quick-prompt. The Copilot responds with a streamed answer, cites her real Safe-to-Spend, and shows a "Based on: Safe-to-Spend engine" trace chip. She feels informed. She closes the app without dread.

**What success looks like:** Priya leaves the app knowing exactly how much she can safely spend and why — without having done any manual work. She does not feel judged. She trusts the number because the app showed its working.

---

## 4. Functional Requirements

Each requirement lists acceptance criteria (AC). Priority: **P0** = MVP-blocking, **P1** = MVP-complete, **P2** = cut first if behind.

---

### FR-1 — Authentication & access (P0) → *capability 1*

- **FR-1.1** Register with email + password; bcrypt-hashed, never stored plaintext; auth token in **httpOnly cookie** (not localStorage) for DPDP compliance and XSS protection.
- **FR-1.2** Registration **auto-authenticates** and redirects immediately to Upload — no email verification for MVP. [NON-GOAL for MVP: email verification — deferred to Phase 2.]
- **FR-1.3** User can log in and log out; protected pages redirect unauthenticated users to login.
- **FR-1.4** All data scoped to `user_id`; no cross-user data access. A test asserts this — no IDOR walks into Phase 2.
- **FR-1.5** **Trust signal** ("No guessing. No shame.") appears above the form fields — functionally required, removal fails acceptance. Password field includes a show/hide toggle.
- **FR-1.6** "Email already registered" error embeds an inline "Log in instead?" link.
- **FR-1.7** T&C and Privacy links open in an **in-page modal** (not a new tab); no pre-ticked consent checkboxes (DPDP Rule 4).
- **FR-1.8** Validation fires **on blur**, clears on input — on-submit-only validation is not acceptable.
- **FR-1.9** Auto-auth transition: `aria-live="assertive"` on confirmation headline; manual fallback link surfaces after 3 s if redirect has not fired; `?fail=1` error state must not auto-redirect.

**AC:** register → auto-redirect to Upload → log out → log back in → see only own data; token in httpOnly cookie; trust signal above form; cross-user isolation test passes.

---

### FR-2 — Statement upload & extraction (P0) → *capabilities 2, 3(extract)*

- **FR-2.1** Upload **CSV** bank statement; map columns to the **canonical transaction schema** (≥2 common Indian-bank CSV shapes supported).
- **FR-2.2** Upload **text-based PDF**; extract via statementsparser → pdfplumber → camelot → LLM-text fallback.
- **FR-2.3** Normalize to canonical schema, de-duplicate (hash of date+amount+description), persist.
- **FR-2.4** Scanned/image PDF detected and **honestly refused** with plain-language message — no silent failure. [NON-GOAL for MVP: OCR of scanned PDFs.]
- **FR-2.5** Upload screen framed as **"Step 1 of 3"** (Upload → Review → Dashboard) — functional onboarding contract, not decoration.
- **FR-2.6** Parse progress shows **4 named real-server-state steps**: *Reading PDF* → *Identifying Transactions* → *Categorising by Rules* → *AI Assist*. Transport: WebSocket push preferred; 1-second polling as MVP fallback. [ASSUMPTION: WebSocket available in Reflex — validate Day 1.]
- **FR-2.7** Completion summary shows honesty breakdown: **"{n} by rules · {n} by AI · {n} need your help"** — derived from real parse output, not placeholders.
- **FR-2.8** "Review transactions" CTA is `aria-disabled` (not hidden) until parse completes; stays in tab order.
- **FR-2.9** Parse failure shows empathetic copy plus a contact/support link — not a generic error toast.
- **FR-2.10** Back navigation mid-upload prompts a confirmation if upload is in progress.

**AC:** upload the demo statement (HDFC June 2026 CSV/PDF — see `data/demo-data.json`) → correct counts, dates, amounts, debit/credit direction rendered; re-upload creates no duplicates; scanned PDF returns honest refusal; parse steps fire in sequence; completion summary shows real counts (24 total, 18 rules, 3 AI, 3 need-help for the demo fixture).

---

### FR-3 — Automatic categorization (P0) → *capability 3(categorize)*

- **FR-3.1 Tier 1 (rules):** deterministic keyword/merchant-pattern matching for common Indian transactions; instant, free.
- **FR-3.2 Tier 2 (LLM):** uncategorized transactions → Claude `claude-haiku-4-5` with structured-output schema (category **enum** + confidence + reasoning). Enum is hard-constrained — no invented categories. Enum hard-constraint also guards against prompt-injection via hostile merchant strings.
- **FR-3.3** Every transaction stores `category_source` (rule|llm|user) and `category_confidence`.
- **FR-3.4 Tier 3 ("Teach Me"):** user correction writes a **merchant-level rule** (not a one-off fix); "Re-apply to all matching merchants" toggle defaults ON; persists for future uploads.
- **FR-3.5 Confidence badge system:**
  - `needs_review` → amber "?" badge
  - `ai_categorised` → blue "AI" badge
  - `rule_categorised` → no badge
  - Raw confidence percentages must **never** be shown to the user.
- **FR-3.6** Filter chips dynamically generated from actual parsed categories; "Needs review" chip always present when count > 0.
- **FR-3.7** Transaction list uses **virtual scroll** — standard DOM list not acceptable for 100–300 rows on budget Android.
- **FR-3.8** "Needs review" banner uses **amber tone**, not error red.
- **FR-3.9** "See my Dashboard" CTA always enabled (sticky) — user never blocked in review loop.
- **FR-3.10** Credit/income rows visually distinguished with green treatment.

**AC:** ≥90% of the demo statement's 24 transactions auto-categorized; every remainder resolvable via Teach Me; merchant rule persists across sessions; confidence badges match `category_source`; virtual scroll renders without layout thrash at 300 rows.

---

### FR-4 — Financial engine: Safe-to-Spend (P0) → *capability 5*
> **Deterministic Python. The LLM never computes this number.** This is the product's kill-signal surface.

- **FR-4.1 Formula (of record):**
  ```
  safe_to_spend_today = max(0, (available_balance − reserved_total − buffer) ÷ days_until_next_confirmed_income)
  ```
  Rounded **down** to the nearest ₹10 (never round a spend figure up). `max(0, …)` floor is non-negotiable — Safe-to-Spend is never negative.

- **FR-4.2 Reservation Rule (DD-1 — of record):**
  1. **Known commitment** (confirmed amount + due date) due on-or-before next confirmed income → **always fully reserved**, regardless of proximity window.
  2. **Predicted/uncertain commitment** → reserved only once inside its criticality proximity window; outside the window it lowers Prediction Confidence and is surfaced to the user, but is not subtracted.
  3. **Variable-amount commitment** → reserve the **top of range** (conservative under uncertainty).
  4. Commitment due **on the income day** → reserved against current balance **unless** income confidence is High AND income ≥ commitment.

- **FR-4.3 Commitment criticality tiers:**
  - **Critical** (rent/EMI/insurance): proximity window 7 days; full amount subtracted immediately within window.
  - **Important** (recurring bills): proximity window 5 days; ring-fenced with slight buffer.
  - **Flexible** (discretionary recurring): proximity window 3 days; shown as separate soft total.
  - Conservative default for new commitments: **Important**.

- **FR-4.4 Buffer (DD-2):** default emergency floor **₹2,000**, configurable per user. All engine tests state buffer explicitly.

- **FR-4.5 Two-layer display:** "Today: ₹X" and "After confirmed income on {date}: ₹Y" — these two figures must **never be merged**. [NON-GOAL for MVP: presenting future income as today's balance.]

- **FR-4.6** Conservative under uncertainty: variable bills reserve top-of-range; missing data lowers Prediction Confidence, never inflates Safe-to-Spend.

- **FR-4.7** Freshness caveat displayed on the hero card itself (not buried in footer): "based on your statement up to {statement end date}."

- **FR-4.8 Undetected salary fallback:** if no salary credit detected, the "after salary" row shows "We couldn't detect a salary — add one manually?" — not a zero or error.

- **FR-4.9 Shortfall state:** when `spendable_pool < 0`, Safe-to-Spend is floored to ₹0 and an honest shortfall message surfaces: "Committed bills before payday exceed your balance by ₹{amount} — here's what to do." No crash, no silence.

- **FR-4.10 Live update:** Safe-to-Spend recalculates in the Dashboard hero card when a commitment is added, edited, or deleted from any surface, without a full page reload.

- **FR-4.11 Briefing snapshot vs. live hero (decision of record):** briefing narration = snapshot at generation time; hero card = live. This is intentional, not a bug.

- **FR-4.12 Engine output struct** (what `services/engine/` returns and tests assert on):
  ```
  {
    reserved_total, spendable_pool,
    days_to_income, safe_to_spend_today, safe_to_spend_after_income (nullable),
    prediction_confidence (Low|Medium|High),
    drivers[], data_quality_flags[],
    safety_ok  # bool: every commitment due before next income is covered
  }
  ```

**AC:** the pytest suite in [`safe-to-spend-scenarios.md`](safe-to-spend-scenarios.md) (7 core + 3 boundary + scenario 11 over-conservatism guard + scenario 12 salary-not-detected = 12 total) passes with exact expected outputs, asserting every field of the evidence-pack struct. `safety_ok` is `True` for scenarios 1–9, 11, 12 and `False`-with-honest-shortfall for scenario 10. Rounding: all STS figures end in 0 (e.g. ₹1,250, not ₹1,254). Zero-floor: scenario 10 returns ₹0 with shortfall message, not a negative or crash. Scenario 11 returns non-zero STS (over-conservatism guard, FR-5.8). Scenario 12 returns `safe_to_spend_after_income=null` + `"no_income_detected"` flag (FR-4.8).

---

### FR-5 — Financial engine: Confidence Score (P0) → *capability 6*
> Deterministic Python; two-indicator architecture.

- **FR-5.1 Confidence Score (0–100):** measures financial *preparedness only* (commitment coverage, buffer health, spending pace vs. income, savings trend) — **never** app engagement.
- **FR-5.2 Prediction Confidence (Low|Medium|High):** measures *data completeness* (statement recency, categorization coverage, commitment-detection certainty) — shown alongside the Score, **never conflated** with it.
- **FR-5.3 Event-to-explanation binding:** every score change writes a `score_events` row: (delta, triggering_event, explanation, suggested_action). An unexplained score change is structurally impossible.
- **FR-5.4 Cold start:** compute immediately; Prediction Confidence = Low/Medium with stated reason. Frame as "Confidence grows with more data" — positive framing, not a failure state. No fake neutral-50.
- **FR-5.5 Confidence chip interaction:** tapping the chip surfaces an inline tooltip with distinct copy per level (High / Medium / Low, each in plain language). Raw score numbers are **never** displayed.
- **FR-5.6 "Why?" expandable block:** expandable on the hero card showing a 1–2 sentence explanation traceable to real data. Fallback copy when data insufficient: *"We don't have enough data yet to fully explain this."*
- **FR-5.7 Stale data warning:** when statement data is >30 days old, amber banner above the hero card prompts re-upload.
- **FR-5.8 Counter-metric — over-conservatism guard:** if Safe-to-Spend is ₹0 on a statement with a positive balance and no commitments due this cycle, that is a bug, not a feature. A test must assert that a commitment-free, buffer-covered balance produces a non-zero STS figure.

**AC:** `score_events` assertions per CS-1–CS-4 in [`safe-to-spend-scenarios.md`](safe-to-spend-scenarios.md); chip tooltip fires on tap; stale-data banner fires at >30 days; Score and Safe-to-Spend never contradict (a ₹0 Safe-to-Spend never coexists with a "Well prepared" Score).

---

### FR-6 — Dashboard & daily briefing (P0/P1) → *capabilities 4, 5(explanation), 9*

- **FR-6.1 (P0)** Hero-first layout: Safe-to-Spend card and Confidence chip always above the fold; charts below. Structural non-negotiable.
- **FR-6.2 (P0)** Plain-language **briefing** narrated by Claude — honest, calm, non-judgmental, jargon-free; confidence caveat never buried. Narration explains the engine's evidence pack — **never computes numbers**.
- **FR-6.3 (P1)** Briefing follows Observation → Evidence → Explanation → Action shape.
- **FR-6.4 (P0)** **Persistent left nav** across all four app screens (Transactions / Dashboard / Insights / Copilot).
- **FR-6.5 (P0)** "+ Add a commitment" opens an inline modal (name / amount / due-date / criticality). On save, Safe-to-Spend updates live per FR-4.10.

**Tone contract (non-negotiable for all generated text in FR-6.2/6.3):** honest, calm, non-judgmental. Observation framing ("We noticed…"), not accusation ("You spent too much on…"). Specific copy for edge states (low confidence, shortfall, empty dashboard) in the UX specs; the briefing must not invent copy that contradicts those.

**AC:** dashboard leads with Safe-to-Spend + why, not a chart wall; briefing passes the tone contract (reviewable via the demo run); every number in prose matches engine output exactly; left nav present on all app screens; inline modal updates Safe-to-Spend without page reload.

---

### FR-7 — AI Copilot (P0/P1) → *capability 7*

- **FR-7.1 (P0)** Chat interface; responses stream token-by-token (async Reflex `State` handler yielding Claude's stream).
- **FR-7.2 (P0)** Copilot answers using **read-only tools** over real data (`get_safe_to_spend`, `get_confidence_score`, `query_transactions`, `get_spending_by_category`, `get_upcoming_commitments`) — never invents numbers, never performs a financial action.
- **FR-7.3 (P0) Hardcoded LLM system-prompt rules (non-configurable):**
  1. Never invent or estimate financial figures — only cite values from tool results.
  2. Express uncertainty explicitly when data is incomplete.
  3. Never give investment recommendations (SEBI IA boundary).
  4. Always populate the `trace` field citing data sources used.
- **FR-7.4 (P0) SSE event schema:**
  - `{ type: 'token', text: string }` — streamed content
  - `{ type: 'trace', sources: [...] }` — server-generated data trace
  - `{ type: 'done' }`
- **FR-7.5 (P0) Trace chips:** every data-citing response shows "Based on: …" chips below the bubble. Tapping a chip navigates to the underlying data view.
- **FR-7.6 (P0) "I don't know" as a valid response:** insufficient-data queries return a graceful honest response with guidance ("I don't have enough data for that — uploading another statement would help"). A confident-sounding wrong answer is worse than an honest admission.
- **FR-7.7 (P1)** Quick-prompt buttons (e.g., "Can I afford ₹___ this weekend?").
- **FR-7.8 (P1)** Context handoff from Insights: pre-populated input + "Talking about: {pattern name}" dismissable chip; `insight_id` in POST body.
- **FR-7.9 (P1)** Chat history stored **server-side** (not localStorage), scoped to `user_id`.
- **FR-7.10 (P1)** Accessibility: `role="log"` + `aria-live="polite"` on chat thread; stream announces completed sentences only; send button uses `aria-disabled`.

**AC:** 10 scripted questions answered with zero invented numbers (verifiable against `copilot_samples` in `demo-data.json`); every data-citing response has trace chips; out-of-scope query returns a graceful honest response (not silence or hallucination); "Can I afford ₹3,000?" reasons over the real Safe-to-Spend.

---

### FR-8 — Proactive insights (P0/P1) → *capability 8*

- **FR-8.1 (P0)** Deterministic pandas detectors surface ≥3 named patterns from: post-payday spike, death-by-small-purchases, zombie subscriptions, weekend-vs-weekday pace, upcoming-commitment collision. All five detectors must be coded; ≥3 must fire on the demo statement. [NOTE FOR PM: "≥3 must fire" means the demo data must be constructed to trigger at least 3 — validate against `demo-data.json` Day 1.]
- **FR-8.2 (P0)** Each insight narrated in Observation → Evidence → Explanation → Action shape. **Evidence must cite 2–3 exact data points** (specific dates, merchant names, exact amounts) in a visually distinct evidence block. "Exact data, never invented or approximated" is a hard constraint enforced in the LLM system prompt.
- **FR-8.3 (P0) SEBI IA boundary on Action layer:** Action may suggest the user *consider* a change; it must never prescribe. Allowed: "You might consider…", "It could be worth checking…". Not allowed: "You should…", "We recommend you…".
- **FR-8.4 (P0) Insight lifecycle:**
  - `seen`: soft fade on scroll past (not removal).
  - `dismissed`: `POST /insights/{id}/dismiss`; insight moves to collapsed "Dismissed" section.
  - `all dismissed` empty state: graceful copy, not a blank page.
  - `insufficient data` (<30 transactions): positive framing ("Upload more statements to see your patterns").
- **FR-8.5 (P0)** When `data_months < 3`, footer note: "More data sharpens these patterns."
- **FR-8.6 (P1)** Insights woven into the briefing.

**AC:** ≥3 insights fire on the demo statement (24 transactions, June 2026 Priya dataset); each evidence block names specific merchants/amounts/dates from `demo-data.json`; SEBI phrasing rule verified in generated text; dismiss endpoint works and insight moves to collapsed section; insufficient-data state shows positive copy.

---

### FR-9 — Commitments management (P1) → *supports FR-4/FR-5*

- **FR-9.1 (P1)** Detect recurring obligations (similar amount ±10%, ~monthly cadence); proactively surface: "We noticed a ₹8,500 charge every 5th — is this an EMI?" — user confirms or dismisses.
- **FR-9.2 (P1)** User can add/edit/delete commitment: name, amount, due-day, criticality (Critical / Important / Flexible per FR-4.3). Default: **Important**.
- **FR-9.3 (P1)** `due_day=31` maps to last day of shorter months; displayed as "end of month."
- **FR-9.4 (P1)** `POST /commitments` and `PATCH /commitments/{id}` responses include `safe_to_spend_updated` so the client updates the Dashboard without a separate fetch.

**AC:** EMI-like patterns detected and surfaced for confirmation; manual commitments feed Safe-to-Spend ring-fencing per FR-4.2; `due_day=31` renders as "end of month" in February; Safe-to-Spend updates live after save.

---

## 5. Non-Functional Requirements

- **NFR-1 Honesty & safety (hard):** no displayed number may cause a missed committed obligation; conservative-by-default; any pipeline failure degrades to a visible, plainly-worded state — never a silent wrong number. LLM must not be in the computation path for Safe-to-Spend or Confidence Score.
- **NFR-2 Local & single-user:** runs on `reflex run`; no cloud accounts required; data in local SQLite.
- **NFR-3 Separation of computation & narration:** all money math is deterministic, unit-tested Python in `services/engine/`; LLM confined to language in `services/narrate/`. This boundary is architectural, not stylistic.
- **NFR-4 Cost & model routing:** total Claude API spend for build + demo cycle < $15. **`claude-haiku-4-5`** for Tier-2 categorization; **`claude-opus-4-8`** (or `claude-sonnet-5` as cost lever) for briefing narration and Copilot. Batch API for bulk categorization; prompt caching for system prompts (~90% saving on cached portion).
- **NFR-5 Privacy/provenance:** data stays local; only transaction text needed for categorization/Q&A sent to Claude API; UI states this boundary. Secrets in `.env` (git-ignored). Auth token in httpOnly cookie.
- **NFR-6 Migratability:** business logic in framework-agnostic `services/`; Reflex `State` orchestrates only. Phase 2 (FastAPI, Postgres, WhatsApp/AA) is a re-skin, not a rewrite.
- **NFR-7 Localization format:** `formatINR()` (Indian number grouping: ₹1,25,000) and `formatDate()` (ISO → "30 Jun 2026") are **required shared utilities** used in all currency and date displays. Non-standard formatting fails acceptance.
- **NFR-8 Accessibility baseline:** `role="log"` + `aria-live="polite"` on Copilot chat thread; `aria-live="assertive"` on auto-auth transition headline; `aria-disabled` (not `disabled`) on not-yet-active CTAs.
- **NFR-9 Performance baseline:** statement parse completes in <60 s for a standard 3-month PDF on a developer laptop. Dashboard initial render <3 s after parse. These are the bounds — "fast" and "responsive" are not acceptable substitutes.

---

## 6. Technical Architecture (of record: the research doc)

Modular monolith in **Reflex** (pure Python → React frontend + FastAPI/Starlette backend). Stack: Reflex · reflex-local-auth · `rx.Model`/sqlmodel → SQLite · `rx.plotly` · pdfplumber/camelot/statementsparser + pandas · Anthropic Claude (**`claude-haiku-4-5`** for categorization, **`claude-opus-4-8`**/**`claude-sonnet-5`** for narration + Copilot; structured outputs, read-only tool use, streaming, prompt caching). **Load-bearing rule:** `services/engine/` (deterministic) is strictly separated from `services/narrate/` (LLM). Full detail, data schema, 3-day plan, and risk register in [technical research document](planning-artifacts/research/technical-ai-financial-copilot-mvp-technical-architecture-stack-research-2026-07-07.md) — treat as the architecture spec.

---

## 7. Data Model (canonical)

| Table | Key fields |
|---|---|
| `users` | id, email, password_hash, created_at |
| `uploaded_files` | id, user_id, filename, upload_at, parse_status |
| `transactions` | id, user_id, source_file_id, date, description_raw, merchant_normalized, amount, **direction** (`credit`\|`debit`), balance_after, category, category_source (`rule`\|`llm`\|`user`), category_confidence |
| `merchant_rules` | id, user_id, pattern, category, source (`system`\|`learned`) |
| `commitments` | id, user_id, name, amount, due_day, criticality (`critical`\|`important`\|`flexible`) |
| `score_events` | id, user_id, score, delta, trigger_event, explanation, suggested_action, timestamp |
| `insights` | id, user_id, pattern_name, observation, evidence (JSON), explanation, action_suggestions (JSON), confidence, data_months, seen (bool), dismissed (bool) |
| `chat_messages` | id, user_id, role (`user`\|`assistant`), content, trace_sources (JSON), timestamp |

Full schema and migration notes in the technical research document.

---

## 8. API Surface (MVP canonical endpoint list)

> `demo-data.json` in the prototype is the reference payload shape for all GET endpoints.

| Endpoint | Method | Purpose / Key payload |
|---|---|---|
| `/auth/register` | POST | Register + auto-auth; set httpOnly cookie |
| `/auth/login` | POST | Log in; set httpOnly cookie |
| `/auth/logout` | POST | Clear session |
| `/statements/upload` | POST | Upload PDF/CSV; returns `{ file_id, status }` |
| `/statements/{id}/status` | GET/WS | Parse progress — WS preferred, polling fallback; emits named step events |
| `/statements/{id}/transactions` | GET | Transaction list with category/confidence/badge |
| `/transactions/{id}/categorise` | PATCH | User correction; writes merchant rule; returns updated matches |
| `/dashboard` | GET | `{ safe_to_spend_today, safe_to_spend_after_income, confidence, confidence_explanation, briefing_text, data_date, commitments[], spending_by_category[] }` |
| `/insights` | GET | `[{ id, pattern_name, observation, evidence[], explanation, action_suggestions[], confidence, data_months }]` |
| `/insights/{id}/dismiss` | POST | Mark insight dismissed |
| `/commitments` | GET, POST | List / add; POST returns `safe_to_spend_updated` |
| `/commitments/{id}` | PATCH, DELETE | Edit / delete; returns `safe_to_spend_updated` |
| `/copilot/chat` | POST | SSE stream: `token` / `trace` / `done` event types |

---

## 9. Success Metrics (MVP acceptance)

1. All 9 capabilities demonstrable end-to-end on the demo statement (HDFC June 2026 Priya dataset).
2. `services/engine/` pytest suite green across all 12 scenarios in [`safe-to-spend-scenarios.md`](safe-to-spend-scenarios.md) (7 core + 3 boundary + over-conservatism guard + salary-not-detected), asserting all evidence-pack struct fields.
3. ≥90% of demo statement's 24 transactions auto-categorized; every remainder resolvable via Teach Me.
4. Every displayed number traceable: source data → engine evidence pack → narration.
5. Copilot answers 10 scripted questions with zero invented numbers; trace chips present on all data-citing responses.
6. Honesty layer spot-check: freshness caveat on hero card; confidence rendered as chip only (no raw number); "Why?" expandable works; parse summary shows real counts; Copilot "I don't know" fires on out-of-scope query; SEBI phrasing rule obeyed in all generated Insight Action text.
7. Post-use self-check: a test user reports feeling more informed/confident than before (the JTBD proxy).

**Counter-metric:** Safe-to-Spend is never ₹0 on a statement with a positive balance and no commitments due this cycle (over-conservatism guard, FR-5.8).

---

## 10. Risks

Top four (full register in the technical research document):
1. PDF layout defeats parsers → test real statements Day-1-hour-1; CSV is guaranteed fallback.
2. Copilot states a wrong number → numbers only via read-only tools over the deterministic engine; enforced by hardcoded system-prompt rules.
3. Safe-to-Spend wrong on edge dates → the pytest scenario suite is the gate; boundary cases 8–10 specifically cover these.
4. Reflex learning curve vs. 3-day clock → front-load ramp Day 1; Streamlit escape hatch if needed; `services/` is framework-agnostic.

---

## 11. Resolved decisions

| Decision | Resolution |
|---|---|
| Data latency/freshness | "Based on your statement up to {date}" on hero card; 30-day amber banner. |
| Confidence Score cold start | Compute immediately; Prediction Confidence Low with reason; "Confidence grows with more data" framing. |
| Multi-bank gap | Single-statement MVP with explicit caveat; multi-account is Phase 2. |
| Briefing vs. live hero | Briefing = snapshot at generation time; hero = live current figure. Intentional. |
| Navigation architecture | Persistent left nav across all 4 app screens. |
| Commitment criticality tiers | Critical / Important / Flexible with distinct ring-fencing; default = Important. |
| Chat history storage | Server-side, scoped to `user_id`. |
| Salary not detected | Graceful prompt, not zero or error. |
| Safe-to-Spend floor | `max(0, …)` — never negative; honest shortfall message when pool < 0. |
| Rounding | Floor to nearest ₹10 — never round up. |
| Engine output struct | Defined in FR-4.12; tests assert every field. |

---

## 12. Open items (carry to build)

| ID | Severity | Item | Owner | Resolve condition |
|---|---|---|---|---|
| X1 | Recommended | UX scenarios assume mobile-responsive web; `ux-spec-mvp.md` is silent on responsive. Reconcile device framing before implementation begins. | PM | Before Day 1 build start |
| R1 | Recommended | Add an explicit Definition-of-Done line to Scenario 01 in UX Scenarios. | UX | Before acceptance testing |
| R2 | Recommended | Disambiguate Scenario 02's `🚀 P2` summary tag (trigger-map tier, not build priority — E7 Commitments is P1 must-ship). | PM | Before story creation |
| O2 | Optional | Clarify whether "Commitments Management" is a standalone page or a Dashboard section for Phase 2 scope planning. | PM | Before Phase 2 kick-off |

---

## 13. Glossary

| Term | Definition |
|---|---|
| **Safe-to-Spend (STS)** | The deterministic daily-spend figure computed by `services/engine/`; always floored at ₹0; rounded down to nearest ₹10. Two-layer: Today and After Confirmed Income. |
| **Confidence Score** | 0–100 deterministic score measuring financial *preparedness* (commitment coverage, buffer health, spending pace, savings trend). Never measures app engagement. Never shown as a raw number in the UI. |
| **Prediction Confidence** | Low / Medium / High indicator measuring *data completeness* (statement recency, categorization coverage, commitment-detection certainty). Shown alongside the Confidence Score; never conflated with it. |
| **Evidence pack** | The struct returned by `services/engine/` — see FR-4.12. Contains `reserved_total`, `spendable_pool`, `days_to_income`, `safe_to_spend_today`, `safe_to_spend_after_income`, `prediction_confidence`, `drivers[]`, `data_quality_flags[]`, `safety_ok`. |
| **Ring-fencing** | Reserving committed expense amounts from the spendable pool so Safe-to-Spend can never cause a missed obligation. |
| **Proximity window** | The number of days before a commitment's due date within which it is ring-fenced: 7d (Critical), 5d (Important), 3d (Flexible). |
| **Canonical transaction schema** | The normalized row shape all uploaded statements are mapped to before persistence: id, user_id, source_file_id, date, description_raw, merchant_normalized, amount, direction, balance_after, category, category_source, category_confidence. |
| **direction** | Enum on `transactions`: `credit` (money in) or `debit` (money out). |
| **Honesty spine** | The non-negotiable product principle: every number traceable (data → engine → evidence pack → narration); LLM never in the computation path; conservative under uncertainty; observable failure states never silent. |
| **Kill-signal** | A Safe-to-Spend error that causes a user to miss a real committed obligation — triggers immediate feature pause and trust audit before relaunch. |
| **Tone contract** | The non-negotiable voice rules for all LLM-generated text: honest, calm, non-judgmental; observation framing, not accusation; SEBI IA boundary on Action suggestions (suggest consideration, never prescribe). |
| **score_events** | The log table binding every Confidence Score change to a triggering event and explanation. An unexplained score change is structurally impossible. |
| **Teach Me** | The user-correction flow that writes a merchant-level categorization rule and re-applies it to all matching transactions across the user's statement history. |

---

*Finalized 2026-07-08 by BMAD — incorporates Step 13 (original build-handoff), Step 16 (scope decision), Steps 17–22 (UX design + prototype), and Step 23 (bmad-prd Update + Finalize pass). Pairs with [`epics-and-stories.md`](epics-and-stories.md) and [`prototypes/01-priyas-first-honest-morning-Prototype/HANDOFF.md`](../../prototypes/01-priyas-first-honest-morning-Prototype/HANDOFF.md).*
