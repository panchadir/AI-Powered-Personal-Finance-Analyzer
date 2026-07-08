# PRD: AI-Powered Personal Finance Analyzer — Phase 1 MVP

**Created:** 2026-07-08
**Author:** ALPHA
**Status:** Draft for build (3-day MVP)
**Type:** Lean MVP PRD

> **Sources of record:** strategic foundation from [`A-Product-Brief/project-brief.md`](A-Product-Brief/project-brief.md) and [`B-Trigger-Map/`](B-Trigger-Map/); technical architecture of record from [`planning-artifacts/research/technical-ai-financial-copilot-mvp-technical-architecture-stack-research-2026-07-07.md`](planning-artifacts/research/technical-ai-financial-copilot-mvp-technical-architecture-stack-research-2026-07-07.md); Safe-to-Spend/Confidence-Score design from [`problem-solution-2026-07-07.md`](problem-solution-2026-07-07.md). This PRD does **not** restate those — it turns them into buildable requirements.

---

## 1. Overview & Goal

**Product job-to-be-done:** turn financial confusion into financial confidence for a financially-capable-but-overwhelmed salaried user — by showing them, from their own bank statement, how much they can safely spend, how prepared they are, and why, in plain language they trust.

**Phase 1 MVP goal:** prove the core experience locally, end-to-end, in a **3-day build**. A user uploads a bank statement and leaves the app **more informed and more confident about their money than when they opened it** — with every number honestly explained and never overstated.

**The one thing that must be true:** every displayed number is traceable (source data → deterministic engine → evidence pack → plain-language narration), and the app never states a spend figure that would cause the user to miss a committed obligation.

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

### Demo scope: golden path (must-ship) vs. stretch (2026-07-08 re-cut)
Nine capabilities in a 3-day solo build is optimistic. The **golden path** — capabilities **1–6** (auth → upload → categorize → dashboard → Safe-to-Spend → Confidence Score, each explained) — fully satisfies the job-to-be-done ("leaves more informed and confident") and is the pass/fail MVP. Capabilities **7 (Copilot)** and **8 (Insights)** are **demo-stretch**: build in priority order on Day 3 if the engine gate is green and time remains; if cut, the MVP still passes. **Do not** replace the Copilot's read-only-tool path with a shortcut that lets the LLM state numbers from memory — that breaks the honesty spine (better to cut it than fake it).

### Out of scope (deferred to Phase 2+ — deferred, not dropped)
Account Aggregator / FIU integration · WhatsApp delivery · DPDP consent-manager architecture · native mobile app · cloud deployment · multi-account reconciliation · scanned/image-PDF OCR · vernacular statement parsing at scale · real-time bank sync. The MVP uses **uploaded statements only** and runs **locally, single-user**.

---

## 3. Target User

**Primary — "Priya"** (per Trigger Map): salaried, Tier-1/2 India, fixed monthly income, EMI-carrying, financially capable but emotionally overwhelmed; avoids her banking app; wants guidance, not homework. The MVP is built and demoed for this persona. (Rohan/Kavya secondary/tertiary personas are Phase 2+; see Trigger Map.)

**MVP data assumption:** predictable salaried income with an identifiable recurring credit — the Safe-to-Spend formula's reliability depends on it. Irregular-income users are explicitly out of Phase 1 scope.

---

## 4. Functional Requirements

Each requirement lists acceptance criteria (AC). Priority: **P0** = MVP-blocking, **P1** = MVP-complete, **P2** = cut first if behind.

### FR-1 — Authentication & access (P0) → *MVP capability 1*
- FR-1.1 A user can register with username/email + password; passwords are bcrypt-hashed, never stored plaintext.
- FR-1.2 A user can log in and log out; protected pages redirect unauthenticated users to login.
- FR-1.3 All data is scoped to the logged-in `user_id`; no user can see another user's data.
- **AC:** register → log out → log back in → see only your own data; password never appears in DB or logs. **A test asserts cross-user isolation** (user B's session cannot read user A's transactions/commitments/chat by id) — FR-1.3 is verified, not just asserted, so no IDOR walks into Phase 2.

### FR-2 — Statement upload & extraction (P0) → *capabilities 2, 3(extract)*
- FR-2.1 User can upload a **CSV** bank statement; columns are mapped to the canonical transaction schema (support ≥2 common Indian-bank CSV shapes).
- FR-2.2 User can upload a **text-based PDF** statement; transactions are extracted (statementsparser where supported → pdfplumber → camelot fallback → LLM-text fallback for unrecognized layouts).
- FR-2.3 Extracted rows are normalized to the canonical schema, de-duplicated (hash of date+amount+description), and persisted.
- FR-2.4 If a PDF has no text layer (scanned image), the app **detects and honestly refuses** it with a plain-language message — no silent failure, no wrong data.
- **AC:** upload a real statement → correct transaction count, dates, amounts, and debit/credit direction render in a table; re-uploading the same file creates no duplicates; a scanned PDF produces an honest "I can't read this one" message.

### FR-3 — Automatic categorization (P0) → *capability 3(categorize)*
- FR-3.1 **Tier 1 (rules):** deterministic keyword/merchant-pattern matching categorizes common Indian transactions (UPI/NEFT/IMPS counterparties, major merchants, rent/EMI patterns) instantly and free.
- FR-3.2 **Tier 2 (LLM):** remaining uncategorized transactions are sent to Claude in batches with a **structured-output schema** (category enum + confidence + reasoning); categories are constrained to the enum (no invented categories). **Model:** default to **`claude-haiku-4-5`** for categorization — it is a constrained-enum classification task, and Haiku is ~5× cheaper and lower-latency than Opus (latency matters on Day 1 when ingestion re-runs often). Keep the enum hard-constrained (this is also the prompt-injection guard against a hostile merchant string).
- FR-3.3 Every transaction stores `category_source` (rule|llm|user) and `category_confidence`.
- FR-3.4 **Tier 3 ("Teach Me"):** a user correction writes a new Tier-1 merchant rule and re-applies it to matching transactions.
- **AC:** ≥90% of transactions on the demo statement are categorized without user help; each remaining one is resolvable via Teach-Me; a correction persists and auto-categorizes future matching merchants.

### FR-4 — Financial engine: Safe-to-Spend (P0) → *capability 5(number)*
> **Deterministic Python. The LLM never computes this number.** Unit-tested — this is the product's kill-signal surface.
- FR-4.1 Compute Safe-to-Spend = `(known balance − ring-fenced commitments − buffer) ÷ days until next confirmed income`.
- FR-4.2 **Proximity-weighted ring-fencing:** critical commitments (rent/EMI/insurance) locked ~7 days out, medium ~5, low ~3; commitments inside the window are fully subtracted regardless of confidence.
- FR-4.3 **Two-layer display:** "Today: ₹X" and "After confirmed income on {date}: ₹Y" — never present future income as today's balance.
- FR-4.4 Conservative under uncertainty: variable bills reserve top-of-range; missing data lowers Prediction Confidence, never inflates Safe-to-Spend.
- FR-4.5 Freshness caveat: every figure carries "based on your statement up to {statement end date}".
- **AC:** the pytest scenario suite in [`safe-to-spend-scenarios.md`](safe-to-spend-scenarios.md) (7 core scenarios + 3 boundary cases: due-date today, payday tomorrow, negative balance) passes with exact expected outputs; Safe-to-Spend never recommends spending that would miss a ring-fenced commitment. **Reservation Rule (DD-1) and buffer (DD-2) are defined in that file — read it before implementing FR-4.1/4.2.**

### FR-5 — Financial engine: Confidence Score (P0) → *capability 6*
> Deterministic Python; two-indicator architecture.
- FR-5.1 **Confidence Score (0–100)** measures financial *preparedness only* (commitment coverage, buffer health, spending pace vs. income, savings trend) — **never** app engagement.
- FR-5.2 **Prediction Confidence (Low/Med/High)** measures *data completeness* (statement recency, categorization coverage, commitment-detection certainty) and is shown alongside, never conflated.
- FR-5.3 **Event-to-explanation binding:** the score is rendered from a `score_events` log; every change carries (delta, triggering event, explanation, suggested action). An unexplained score change is structurally impossible.
- FR-5.4 Cold start: compute immediately from the uploaded statement with Prediction Confidence Low/Medium and state why — no fake neutral-50.
- **AC:** the visible drivers explain the current score; changing the data produces a `score_events` row with a one-sentence "what changed and why"; score and Safe-to-Spend never tell contradictory stories.

### FR-6 — Dashboard & daily briefing (P0/P1) → *capabilities 4, 5(explanation), 9*
- FR-6.1 (P0) Dashboard shows the Safe-to-Spend hero card, Confidence Score + visible drivers, and category/trend charts (`rx.plotly`) and summaries.
- FR-6.2 (P0) A plain-language **briefing** narrates the numbers via Claude, in the brief's tone of voice (honest, calm, non-judgmental, jargon-free; confidence caveat never buried). **The narration explains the engine's evidence pack — it never computes numbers.**
- FR-6.3 (P1) Briefing follows the Observation → Evidence → Explanation → Action shape.
- **AC:** the dashboard leads with the number + its "why," not a chart wall; the briefing reads as a calm, honest human sentence, not a category dump; every number in prose matches the engine output exactly.

### FR-7 — AI Copilot (P0/P1) → *capability 7*
- FR-7.1 (P0) A chat interface lets the user ask natural-language financial questions; responses stream token-by-token (async Reflex `State` handler yielding Claude's stream).
- FR-7.2 (P0) The Copilot answers using **read-only tools** over the user's real data (`get_safe_to_spend`, `get_confidence_score`, `query_transactions`, `get_spending_by_category`, `get_upcoming_commitments`) — it never invents numbers and never performs a financial action.
- FR-7.3 (P1) "Gut-check" quick-prompt buttons (e.g., "Can I afford ₹___ this weekend?").
- **AC:** 10 scripted questions answered with zero invented numbers; every figure the Copilot states is traceable to a tool call; "can I afford X?" reasons over the real Safe-to-Spend.

### FR-8 — Proactive insights (P1/P2) → *capability 8*
- FR-8.1 (P1) Deterministic pandas detectors surface ≥3 named patterns from: post-payday spike, death-by-small-purchases (repeated small debits), zombie subscriptions (recurring similar debits), weekend-vs-weekday pace, upcoming-commitment collision.
- FR-8.2 (P1) Each insight is narrated in Observation → Evidence → Explanation → Action shape.
- FR-8.3 (P2) Insights woven into the briefing, not just listed.
- **AC:** at least 3 insights fire on a realistic statement; each names a real pattern with the evidence behind it; tone is observation, never accusation.

### FR-9 — Commitments (P1) → *supports FR-4/FR-5*
- FR-9.1 (P1) Detect recurring obligations (similar amount ±10%, ~monthly cadence) from statement history.
- FR-9.2 (P1) User can add/edit/delete a commitment (name, amount, due-day, criticality).
- **AC:** rent/EMI-like patterns are detected; manual commitments feed Safe-to-Spend ring-fencing correctly.

---

## 5. Non-Functional Requirements

- **NFR-1 Honesty & safety (hard):** no displayed number may cause a missed committed obligation; conservative-by-default; any pipeline failure degrades to a visible, plainly-worded state — never a silent wrong number.
- **NFR-2 Local & single-user:** runs on a local dev machine (`reflex run`); no cloud accounts required; data in a local SQLite file.
- **NFR-3 Separation of computation & narration:** all money math is deterministic, unit-tested Python in `services/engine/`; the LLM is confined to language in `services/narrate/`. This boundary is architectural, not stylistic.
- **NFR-4 Cost & model routing:** total Claude API spend for the full build + demo cycle < $15. **Model per task (not one model for all):** **`claude-haiku-4-5`** for Tier-2 categorization (constrained classification; cheap + fast); **`claude-opus-4-8`** (or `claude-sonnet-5` as a cost lever) for the two language surfaces that show quality — briefing **narration** and the **Copilot**. Batch API for bulk categorization; prompt caching for the chat/narration system prompt (~90% saving on the cached portion).
- **NFR-5 Privacy/provenance:** data stays local; only the transaction text needed for categorization/Q&A is sent to the Claude API; the UI states this boundary. Secrets in `.env` (git-ignored), never in code.
- **NFR-6 Migratability:** business logic lives in framework-agnostic `services/`; Reflex `State` classes only orchestrate. Phase 2 (FastAPI backend, Postgres, WhatsApp/AA) is a re-skin, not a rewrite.

---

## 6. Technical Architecture (of record: the research doc)

Modular monolith in **Reflex** (pure Python → React frontend + FastAPI/Starlette backend). Stack: Reflex · reflex-local-auth · `rx.Model`/sqlmodel → SQLite · `rx.plotly` · pdfplumber/camelot/statementsparser + pandas · Anthropic Claude (**`claude-haiku-4-5`** for categorization, **`claude-opus-4-8`**/`claude-sonnet-5` for narration + Copilot — see NFR-4; structured outputs, read-only tool use, streaming, prompt caching). **Load-bearing rule:** `services/engine/` (deterministic) is strictly separated from `services/narrate/` (LLM). Full detail, data schema, 3-day plan, and risk register are in the [technical research document](planning-artifacts/research/technical-ai-financial-copilot-mvp-technical-architecture-stack-research-2026-07-07.md) — treat it as the architecture spec.

---

## 7. Data Model (canonical — see research doc for full schema)

`users` · `uploaded_files` · **`transactions`** (id, user_id, date, description_raw, merchant_normalized, amount, direction, balance_after, category, category_source, category_confidence, source_file_id) · `merchant_rules` (pattern → category, learned) · `commitments` (name, amount, due_day, criticality) · `score_events` (score, delta, trigger_event, explanation, timestamp) · `chat_messages`.

---

## 8. Success Metrics (MVP acceptance)

1. All 9 capabilities demonstrable end-to-end on a real statement.
2. `services/engine/` pytest suite green across all 10 scenarios in [`safe-to-spend-scenarios.md`](safe-to-spend-scenarios.md) (7 core + 3 boundary).
3. ≥90% of demo-statement transactions auto-categorized; every remainder resolvable via Teach-Me.
4. Every displayed number traceable data → engine → evidence pack → narration.
5. Copilot answers 10 scripted questions with zero invented numbers.
6. Post-use self-check: a test user reports feeling more informed/confident than before (the JTBD proxy).

---

## 9. Risks (see research doc for full register + mitigations)

Top four: (1) PDF layout defeats parsers → test real statements Day-1-hour-1, CSV guaranteed fallback; (2) Copilot states a wrong number → numbers only via read-only tools over the deterministic engine; (3) Safe-to-Spend wrong on edge dates → the pytest scenario suite is the gate; (4) Reflex learning curve vs. 3-day clock → front-load ramp Day 1, Streamlit escape hatch, framework-agnostic `services/`.

---

## 10. Resolved-for-MVP decisions (were open in problem-solving session)

- **Data latency/freshness:** display "based on your statement up to {date}" (statement date = freshness).
- **Confidence Score cold start:** compute immediately with visible Low/Medium Prediction Confidence (no fake neutral-50).
- **Multi-bank gap:** single-statement scope for MVP, with an explicit caveat (multi-account reconciliation is Phase 2).

---

*Generated by BMAD — synthesized directly from the Product Brief, Trigger Map, Problem-Solving session, and Technical Research (per the project's established direct-authoring pattern). Pairs with [`epics-and-stories.md`](epics-and-stories.md).*
