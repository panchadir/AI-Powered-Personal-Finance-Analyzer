# 01: Priya's First Honest Morning

**Project:** AI-Powered-Personal-Finance-Analyzer
**Created:** 2026-07-08
**Method:** Whiteport Design Studio (WDS)

---

## Transaction (Q1)

**What this scenario covers:**
Register, auto-authenticate, upload a real bank statement, and move through the full **golden path** — categorized transactions, her first honest Safe-to-Spend briefing and Confidence Score, a proactive insight, and an exploratory first conversation with the Copilot — in one sitting. All seven steps are committed MVP scope.

---

## Business Goal (Q2)

**Goal:** ⭐ PRIMARY GOAL — Measurably reduce financial anxiety (THE ENGINE)
**Objective:** WoZ validation gate — average daily anxiety rating ≥ 3.5/5; Safe-to-Spend understood correctly by 5 of 5 pilot users

---

## User & Situation (Q3)

**Persona:** Priya — The Overwhelmed Earner (Primary)
**Situation:** 32, salaried marketing executive in Mumbai, ~₹65,000/month, EMI-carrying. A colleague just told her "you have to try this one — it's actually honest with you." She's trying it on a quiet evening at home, at her laptop, having just downloaded her bank statement.

---

## Driving Forces (Q4)

**Hope:** Finally get one honest, simple answer to "am I okay?" — without homework or judgment.

**Worry:** It'll be another confident-sounding tool that turns out wrong, or makes her feel behind and ashamed again.

---

## Device & Starting Point (Q5 + Q6)

**Device:** Desktop (localhost web app, single-user browser session)
**Entry:** After a friend's word-of-mouth recommendation, she downloads her bank statement PDF from her banking app, then opens the AI Financial Copilot in her laptop's browser to create an account.

---

## Best Outcome (Q7)

**User Success:**
Priya sees a two-layer Safe-to-Spend number (today + after payday) with one honest sentence of reasoning and a Confidence Score, correctly understands it unaided, sees at least one honest proactive insight, and gets a first taste of the Copilot answering a real question about her own data.

**Business Success:**
WoZ comprehension gate hit — Safe-to-Spend understood correctly — plus the anxiety-reduction signal captured on Day 1, and a demonstration that the Copilot's zero-invented-numbers honesty layer holds up under a first-time user's real question.

---

## Shortest Path (Q8)

1. **Register** — Priya creates her account (email + password)
2. **Login** — auto-authentication confirmation; account ready, no credential re-entry; auto-redirects to Statement Upload
3. **Statement Upload** — she uploads her bank statement PDF and watches honest parsing progress
4. **Dashboard** — parsing complete lands her here directly (changed 2026-07-09, was Transactions Table): she sees her first Safe-to-Spend number, Confidence Score, and plain-language briefing, explained
5. **Transactions Table** — from the Dashboard's "View All Transactions" CTA, she reviews her categorized transactions, corrects one merchant via "Teach Me," then returns to her Dashboard
6. **AI Insights & Recommendations** — from the Dashboard, she sees a proactive, honestly-framed observation about her spending
7. **Copilot Chat** — curious, she asks her first question and gets a real, reasoned answer traced to her own data ✓

---

## Trigger Map Connections

**Persona:** Priya — The Overwhelmed Earner (Primary)

**Driving Forces Addressed:**
- ✅ **Want:** Daily calm without effort
- ❌ **Fear:** Being lied to, or led into harm

**Business Goal:** ⭐ Measurably reduce financial anxiety (THE ENGINE) — WoZ gate: anxiety ≥ 3.5/5, Safe-to-Spend understood by 5/5

---

## Scenario Steps

| Step | Folder | Purpose | Exit Action |
|------|--------|---------|-------------|
| 01.1 | `01.1-register/` | Create her account | Submits registration form → auto-redirect to 01.2 |
| 01.2 | `01.2-login/` | Auto-authentication confirmation (no user action needed) | Auto-redirects to 01.3 |
| 01.3 | `01.3-statement-upload/` | Upload her bank statement | Uploads PDF, sees honest parsing progress → lands on Dashboard |
| 01.5 | `01.5-dashboard/` | See her first honest Safe-to-Spend briefing (default landing page after upload) | Views All Transactions, or her Insights |
| 01.4 | `01.4-transactions-table/` | Review categorized transactions (reached from the Dashboard) | Corrects a merchant via "Teach Me" → returns to Dashboard |
| 01.6 | `01.6-ai-insights-recommendations/` | See a proactive, honest observation about her spending | Opens the Copilot, curious |
| 01.7 | `01.7-copilot-chat/` | Ask her first real question and get a reasoned answer | Final — scenario success ✓ |

**First step** (01.1) includes full entry context (Q3 + Q4 + Q5 + Q6).
**On-step interactions** (that don't leave the step) are documented as storyboard items within each page spec.
**Navigation note (2026-07-09, updated same day):** Steps 01.5 and 01.4 are listed in walkthrough order (Dashboard is the post-upload landing page; Transactions is one click away from it), and all four sidebar screens (Dashboard, Transactions, Insights, Copilot) are reachable from one another at any time via the persistent left sidebar — this scenario is not a strict one-way funnel past Statement Upload. Commitments Management is **not** a sidebar item; it's reached solely via the Dashboard's "+ Add a commitment" CTA (corrected same day — an earlier pass had briefly added it to the sidebar as a 5th item, which over-corrected past FR-6.4's actual 4-screen nav).
