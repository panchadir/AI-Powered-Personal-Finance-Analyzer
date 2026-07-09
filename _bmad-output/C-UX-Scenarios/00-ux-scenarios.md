# UX Scenarios: AI-Powered-Personal-Finance-Analyzer

> Scenario outlines connecting Trigger Map personas to concrete user journeys

**Created:** 2026-07-08
**Author:** ALPHA with Claude Code (UX Scenario Facilitator)
**Method:** Whiteport Design Studio (WDS)

---

## Scenario Summary

| ID | Scenario | Persona | Pages | Priority | Status |
|----|----------|---------|-------|----------|--------|
| 01 | [Priya's First Honest Morning](01-priyas-first-honest-morning/01-priyas-first-honest-morning.md) | Priya (Primary) | 7 | ⭐ P1 | ✅ Outlined |
| 02 | [Priya Protects What Matters](02-priya-protects-what-matters/02-priya-protects-what-matters.md) | Priya (Primary) | 1 | ⭐ P1 | ✅ Outlined |
| 03 | [Priya's Two-Tap Gut-Check](03-priyas-two-tap-gut-check/03-priyas-two-tap-gut-check.md) | Priya (Primary) | 1 | 🚀 P2 | ✅ Outlined |

> **Scope correction (post-outline):** Commitments Management (02.1) is promoted from P2 to **P1/committed**. The Dashboard (P1) already visually depends on commitment data for Safe-to-Spend ring-fencing and its "+Add a commitment" CTA, and `epics.md` Epic 5 already commits the underlying engine/DB work — the standalone page was the only piece still marked P2, an inconsistency rather than an intentional cut.

---

## Scenarios

### [01: Priya's First Honest Morning](01-priyas-first-honest-morning/01-priyas-first-honest-morning.md)
**Persona:** Priya (Primary) — Want: daily calm without effort; Fear: being lied to / led into harm
**Pages:** Register, Login (auto-authentication), Statement Upload, Dashboard, Transactions Table, AI Insights & Recommendations, Copilot Chat
**User Value:** Registers, uploads a statement, and moves through the full golden path in one sitting — understanding her Safe-to-Spend number, a proactive insight, and a first honest Copilot answer, all unaided.
**Business Value:** Exercises the WoZ go/no-go gate (Safe-to-Spend comprehension + anxiety-reduction signal) and demonstrates the Copilot's zero-invented-numbers honesty layer on a first-time user's real question.

---

### [02: Priya Protects What Matters](02-priya-protects-what-matters/02-priya-protects-what-matters.md)
**Persona:** Priya (Primary) — Want: to feel capable, not failing; Fear: the end-of-month shock
**Pages:** Commitments Management *(Login is a prerequisite returning-user entry point, not a numbered scenario step)*
**User Value:** Adds her electricity bill as a protected commitment and sees her Safe-to-Spend recalculate — confident her critical bills can never be silently missed.
**Business Value:** Demonstrates the conservative-by-default ring-fencing mechanism — the kill-signal prevention layer — supporting the "Confidence Score up for ≥80% of users" target.

---

### [03: Priya's Two-Tap Gut-Check](03-priyas-two-tap-gut-check/03-priyas-two-tap-gut-check.md)
**Persona:** Priya (Primary) — Want: decide everyday spending without second-guessing; Fear: being lied to / led into harm
**Pages:** Copilot Chat *(return-visit — distinct from Scenario 01's first-touch Copilot exploration)*
**User Value:** A five-second, guilt-free "yes, that's fine" answer with reasoning on a real ₹1,200 dinner decision.
**Business Value:** Proves the Copilot's habitual return-usage value — the depth behind habit formation, Day-7 retention (≥4/5), and eventually conversion.

---

## Page Coverage Matrix

| Page | Step | Scenario | Purpose in Flow |
|------|------|----------|----------------|
| Register | 01.1 | 01 | Create account |
| Login *(auto-authentication)* | 01.2 | 01 | Confirm account ready; auto-redirect (no user action needed) |
| Statement Upload | 01.3 | 01 | Upload bank statement, watch honest parsing progress → lands on Dashboard |
| Dashboard | 01.5 | 01 | Default landing page post-upload; see first Safe-to-Spend briefing + Confidence Score, explained; "View All Transactions" CTA |
| Transactions Table | 01.4 | 01 | Reached from the Dashboard; review categorized transactions, correct one via "Teach Me" → returns to Dashboard |
| AI Insights & Recommendations | 01.6 | 01 | See a proactive, honestly-framed observation about spending |
| Copilot Chat | 01.7 | 01 | Ask a first exploratory question, get a data-traced answer |
| Commitments Management | 02.1 | 02 | Add electricity bill as a protected commitment; Safe-to-Spend recalculates |
| Copilot Chat *(return-visit)* | 03.1 | 03 | Two-tap gut-check on a real ₹1,200 spending decision |

**Coverage:** 8/8 unique pages assigned to scenarios. *(Copilot Chat is documented as two distinct user moments — first-touch exploration in Scenario 01 and a habitual gut-check in Scenario 03 — a deliberate, transparent exception to strict single-assignment. The returning-user Login page at /login is a shared entry point used before Scenario 02 but is not a numbered Scenario 02 step.)*

---

## Notes on the Revised Flow

The scenario plan was revised at the project owner's direction to reflect the app's actual navigation backbone:

**01.1 Register → 01.2 Login (auto) → 01.3 Statement Upload → 01.5 Dashboard → 01.4 Transactions Table → 01.6 AI Insights & Recommendations → 01.7 Copilot Chat**

*(Updated 2026-07-09 — Dashboard and Transactions Table swapped order. The Dashboard, not the Transactions Table, is now the default landing page immediately after upload, giving Priya a high-level Safe-to-Spend summary before transaction-level detail. Transactions is reached from the Dashboard's "View All Transactions" CTA — see the note below and each page's Entry/Exit Points.)*

Key structural changes from the original plan:
- **Login is now Scenario 01 step 01.2** — the auto-authentication confirmation beat immediately after registration. No credential re-entry; the page resolves itself in < 1 second and redirects. *(Changed post-generation at project owner's request.)*
- **Returning-user Login** (`/login`) is a separate standalone page used before Scenario 02. It is not numbered in the scenario flow.
- **Scenario 02 collapsed to 1 step** — Commitments Management (02.1) is now the sole numbered step; Login is the prerequisite entry.
- **AI Insights & Recommendations** was promoted from an inline Dashboard element to its own page/step.
- **Scenario 03 was repurposed** from a duplicate first-touch Copilot scenario into a distinct habitual return-visit gut-check.
- **Confidence Score Drill-in is committed scope** (correction: this was previously listed here as deferred/out-of-scope, but that was stale — `epics.md` Story 5.2, "Confidence Score Drill-In Panel," is a fully committed, fully-specced story with acceptance criteria. It was never actually cut from the canonical build backlog, only from this overview doc's outdated understanding). Interaction: tapping the Confidence Score chip opens the drill-in panel, showing the Prediction Confidence label/reason plus a reverse-chronological `score_events` history list (delta, explanation, time elapsed). Per FR-5.5, the raw score number is never shown — label only (Well prepared / On track / Watch this).

---

## Next Phase

These scenario outlines feed into **Phase 4: UX Design** where each page gets:
- Detailed page specifications
- Wireframe sketches
- Component definitions
- Interaction details

---

_Generated with Whiteport Design Studio framework_
