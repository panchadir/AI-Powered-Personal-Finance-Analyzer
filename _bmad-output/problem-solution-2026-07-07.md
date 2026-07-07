# Problem Solving Session: Safe-to-Spend Formula & Confidence Score Design

**Date:** 2026-07-07
**Problem Solver:** ALPHA
**Problem Category:** Product Design / AI System Design

---

## 🎯 PROBLEM DEFINITION

### Initial Problem Statement

Two interconnected product design problems that must be solved before MVP build:

**A.** How do we design a Safe-to-Spend formula that is accurate, conservative enough to prevent financial harm, yet realistic enough to be genuinely useful?

**D.** How do we design a Confidence Score that feels earned, is emotionally legible, and drives a daily habit loop without becoming a vanity metric?

### Refined Problem Statement

> **How do we build a financial intelligence engine — expressed as Safe-to-Spend and Confidence Score — that is simultaneously conservative enough to never cause financial harm, honest about its own uncertainty, and emotionally legible to a user who doesn't trust numbers she cannot explain?**

The core tension: precision vs. safety vs. simplicity. Too precise = dangerous when data is incomplete. Too conservative = useless and frustrating. Too complex = opaque and untrustworthy.

### Problem Context

**From prior sessions (Brainstorming, Design Thinking, Innovation Strategy):**
- Core persona: Priya, 32, salaried professional, Mumbai. Financially capable but emotionally overwhelmed.
- Product vision: AI Financial Copilot that turns financial confusion into financial confidence.
- The morning briefing is the front door. Safe-to-Spend is the headline number. Confidence Score is the spine.
- Trust is the moat. One wrong Safe-to-Spend that causes an overdraft = user churned forever.
- Phase 1 focus: salaried users with predictable income. Irregular income deferred to Phase 2.
- Working hypothesis formula: Confirmed Income − Committed Expenses − Buffer ÷ Days Remaining.
- Formula result must be accompanied by plain-language explanation — never a raw equation.

**Failure modes identified:**
- A-CRITICAL: False confidence — telling users they're safe when a committed expense (rent, EMI, insurance) will be missed. Trust destroyed immediately.
- A-SECONDARY: Overcorrection — consistently underestimating Safe-to-Spend, making the AI feel unnecessarily restrictive.
- D-CRITICAL: Score changes without explanation — feels random, users disengage within days.
- D-SECONDARY: Score rewards app engagement instead of financial progress — becomes vanity metric.
- D-TERTIARY: Score stays static for long periods — no visible momentum, habit loop breaks.

### Success Criteria

**Safe-to-Spend (A):**
- Never recommends spending that causes a user to miss a committed financial obligation
- Recalculates dynamically when new transactions, bills, or income events occur
- Presents result with natural-language explanation of *why* (not a formula)
- Handles uncertainty conservatively with visible confidence indicators
- Accurate enough that 95%+ of recommendations are within 10% of what a careful human CFO would advise

**Confidence Score (D):**
- Every score change accompanied by: what changed, why, what action caused it, what to do next
- Primarily measures financial preparedness (bill coverage, emergency buffer, cash-flow stability)
- Behavioral actions (logging, correcting AI, following recommendations) have secondary influence only
- Shows visible momentum within first 7 days for a typical new user
- Always answers three questions: *Why is my score X today? What changed? What can I do to improve it?*
- Score never contradicts Safe-to-Spend — they must tell the same financial story

---

## 🔍 DIAGNOSIS AND ROOT CAUSE ANALYSIS

### Problem Boundaries (Is/Is Not)

**WHERE the problem lives:**
- Safe-to-Spend failure risk: morning briefing display, gut-check moments, unexpected bill recalculation
- Confidence Score failure risk: any score change event without accompanying explanation
- NOT in: transaction feed, category view, investment screens, B2B2C context (Phase 1)

**WHEN the problem is most dangerous:**
- Incomplete or lagged bank data + imminent committed expense (rent/EMI within 3–7 days) — highest stakes
- First 30 days before behavioral history established AND at variable-expense moments regardless of tenure
- When income hasn't arrived yet (low balance day before payday)
- NOT when: all accounts connected, data fresh, stable month, all commitments just paid

**WHO is in scope:**
- Phase 1: salaried users with predictable income and at least one AA-connected account
- Both "trusting Priya" (acts on Safe-to-Spend directly) and "skeptical Priya" (cross-checks against bank app) — both are design targets
- NOT in scope Phase 1: freelancers, gig workers, manual-entry-only users (insufficient data for formula reliability)

**WHAT the problem is — and isn't:**
- IS: formula behavior under incomplete/uncertain data; score legibility when it changes
- IS: communication design — accuracy without explainability still fails
- IS NOT: a UI problem, a categorization accuracy problem, a gamification problem
- IS NOT: forecasting accuracy in isolation — the formula can be right and still fail if it can't explain itself

**Boundary Decision 1 — Income not yet arrived:**
Safe-to-Spend always reflects current reality with confirmed future income as a transparent, separate layer:
- "Today's Safe-to-Spend: ₹150"
- "After your confirmed salary tomorrow: ₹2,850"
- Anticipated income only used when historically reliable (recurring salary with consistent arrival pattern)
- Principle: never present tomorrow's money as today's money. Say what you know, say what you expect, say why.

**Boundary Decision 2 — Engagement vs. preparedness:**
The Confidence Score measures financial preparedness only — never app engagement.
- Priya offline for a week, bills covered, buffer healthy → score stays high. Her finances didn't deteriorate.
- Engagement (connecting accounts, correcting categories, uploading statements) improves AI data quality → indirectly improves score accuracy → but never artificially inflates it
- **Product principle (first-class, non-negotiable):** *"The Confidence Score rewards financial readiness, not product usage."*

**Two-indicator architecture (design decision):**
Separate the two orthogonal concerns cleanly:
- 🛡️ **Confidence Score (0–100):** How financially prepared is the user based on known data?
- 🎯 **Prediction Confidence (Low / Medium / High):** How certain is the AI about its assessment given data completeness?
- Example: "Score: 87/100 — you're well prepared. Prediction Confidence: Medium — some cash transactions missing; recommendation is conservative until data improves."
- These two numbers tell different stories and must never be conflated.

**Pattern that emerged:**
The danger zone is not inaccuracy in general — it is confident wrongness 3 days before a committed expense. Both problems collapse to the same root: **how does the system behave under uncertainty?** The formula under incomplete data and the score under unexplained change are the same challenge wearing different clothes.

### Root Cause Analysis

**Root Cause A — Safe-to-Spend Critical Failure Path:**

Five Whys trace: Safe-to-Spend shows ₹3,000 → Priya spends it → misses EMI
1. EMI not reflected in committed expenses at calculation time
2. EMI either never detected, or detected but timing was wrong
3. Due-date prediction off because EMI dates vary ±2 days (weekend shifts, bank processing delays)
4. Formula treats "due in 5 days" and "due in 2 days" identically — no proximity sensitivity
5. **Root cause: formula lacks a proximity-weighted commitment lock.** Committed expenses within a critical window must be fully ring-fenced from Safe-to-Spend regardless of prediction confidence.

**Root Cause D — Confidence Score Legibility Failure:**

Fishbone trace: Score drops 74 → 69 with no explanation → Priya feels confused and blamed
- Score engine and explanation engine are architecturally decoupled — score can update without triggering an explanation
- No "score changelog" concept — deltas displayed but delta-reasons not surfaced
- Users have no mental model for what the score measures → any movement feels arbitrary
- Score reacts to events (new bill, spending pace change) but does not narrate them
- **Root cause: no event-to-explanation binding.** Every score delta must be causally linked to a specific triggering event; score and explanation are not separable.

### Contributing Factors

**For Safe-to-Spend:**
- Variable recurring bills (utilities, usage-based services) — amount uncertain even when timing is known
- AA data latency — bank transactions may appear 12–24 hours late, creating a stale-data window
- Multi-bank users — committed expense may be paid from Account B while Safe-to-Spend is calculated from Account A balance
- User-added vs. AI-detected commitments — AI may miss a new EMI in the first month before pattern is established

**For Confidence Score:**
- Score dimensions are not visible to the user — preparedness, cash-flow stability, buffer health all feed in silently
- No early momentum design — a new user with good finances but little connected data may start low and improve slowly
- Score contradicting Safe-to-Spend — if score is 80 but Safe-to-Spend is ₹0, the dissonance destroys trust in both

### System Dynamics

**The uncertainty cascade:**
Incomplete data → conservative Safe-to-Spend → low Prediction Confidence displayed → user doesn't act on recommendation → AI gets less behavioral feedback → data remains incomplete → loop repeats.

Breaking this loop requires: (a) making Prediction Confidence visibly improvable by the user, and (b) rewarding data-sharing actions with immediate, visible Safe-to-Spend improvement — not just a score tick.

**The proximity escalation dynamic:**
Adaptive 7-day window design (confirmed):
- Default ring-fencing window: 7 days before committed expense due date
- Window is adaptive, not fixed — governed by expense criticality and amount:
  - Critical commitments (rent, loan EMIs, insurance): gradual influence begins ~7 days out, increasingly conservative as due date approaches
  - Medium commitments (subscriptions, utilities): ring-fenced at ~5 days
  - Low commitments (small recurring services): ring-fenced at ~3 days
- Rationale: 3 days = too reactive (no time to adjust); 14 days = too conservative (frustrates users); 7 days = planning buffer without unnecessary restriction

**The notification intelligence dynamic:**
Score explanation surfacing tiers (confirmed):
- Every score change → explanation always present in-app when user opens (no exception)
- Push notifications reserved for significant/actionable events only:
  - Meaningful score drop from upcoming commitment or cash-flow shortfall
  - Significant improvement from milestone achievement
  - Recommendation requiring timely action
- Minor day-to-day adjustments → silent in-app update only (no push) to prevent notification fatigue
- Principle: the explanation is mandatory; the push is earned by significance

---

## 📊 ANALYSIS

### Force Field Analysis

**Driving Forces (Supporting Solution):**
- AA framework: real bank data, legally clean, no scraping ★★★★★
- LLMs: plain-language explanations at scale, low cost ★★★★★
- Salaried users: highly predictable income — formula inputs are reliable ★★★★
- UPI transaction history: 12+ months of behavioral data available from Day 1 for most urban users ★★★★
- User motivation: Priya *wants* to trust the number — she's hiring a reassurance engine ★★★

**Restraining Forces (Blocking Solution):**
- AA data latency (12–24hr lag): Safe-to-Spend can be stale without user knowing ★★★★★
- Variable recurring bills: amount unknown even when timing is predictable ★★★★
- First 30 days: insufficient history for reliable pattern detection ★★★★
- Multi-bank reality: committed expense paid from Account B, balance read from Account A ★★★
- LLM explanation quality: generic explanations feel hollow; personalized ones require careful prompting ★★★

### Constraint Identification

*[Session paused at Step 4 — three open constraint questions to resolve in next session:]*
- Q1: Data latency handling — visible freshness indicator vs. silent use of last known data?
- Q2: Confidence Score cold start — neutral 50 / data-based calculation / hide until threshold?
- Q3: Multi-bank gap — calculate from connected account with caveat, or require all accounts?

### Key Insights

*[To be completed after constraint questions resolved — Step 4 continuation]*

---

## 💡 SOLUTION GENERATION

### Methods Used

*[To be completed in Step 5]*

### Generated Solutions

*[To be completed in Step 5]*

### Creative Alternatives

*[To be completed in Step 5]*

---

## ⚖️ SOLUTION EVALUATION

### Evaluation Criteria

*[To be completed in Step 6]*

### Solution Analysis

*[To be completed in Step 6]*

### Recommended Solution

*[To be completed in Step 6]*

### Rationale

*[To be completed in Step 6]*

---

## 🚀 IMPLEMENTATION PLAN

### Implementation Approach

*[To be completed in Step 7]*

### Action Steps

*[To be completed in Step 7]*

### Timeline and Milestones

*[To be completed in Step 7]*

### Resource Requirements

*[To be completed in Step 7]*

### Responsible Parties

*[To be completed in Step 7]*

---

## 📈 MONITORING AND VALIDATION

### Success Metrics

*[To be completed in Step 8]*

### Validation Plan

*[To be completed in Step 8]*

### Risk Mitigation

*[To be completed in Step 8]*

### Adjustment Triggers

*[To be completed in Step 8]*

---

## 📝 LESSONS LEARNED

### Key Learnings

*[To be completed in Step 9 — optional]*

### What Worked

*[To be completed in Step 9 — optional]*

### What to Avoid

*[To be completed in Step 9 — optional]*

---

_Generated using BMAD Creative Intelligence Suite - Problem Solving Workflow_
