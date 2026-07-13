---
stepsCompleted: [1, 2]
inputDocuments:
  - '_bmad-output/planning-artifacts/prd.md'
  - '_bmad-output/planning-artifacts/epics.md'
  - '_bmad-output/project-context.md'
workflowType: 'research'
lastStep: 1
research_type: 'market'
research_topic: 'Proactive insight feeds in personal finance apps (India, SEBI-constrained)'
research_goals: 'Identify Insights-feature enhancements BEYOND the current PRD (FR-8.1–FR-8.6) by mapping how competing apps surface proactive insights, and separating table-stakes from genuine differentiators.'
user_name: 'ALPHA'
date: '2026-07-12'
web_research_enabled: true
source_verification: true
---

# Research Report: Market

**Date:** 2026-07-12
**Author:** ALPHA
**Research Type:** Market Research

---

## Research Overview

[Research overview and methodology will be appended here]

---

# Market Research: Proactive Insight Feeds in Personal Finance Apps (India, SEBI-Constrained)

## Research Initialization

### Research Understanding Confirmed

**Topic**: Proactive insight feeds in personal finance apps — how competing products detect, narrate, and surface behavioural money patterns, viewed through an India / SEBI-constrained lens.

**Goals**: Identify enhancements to the Insights feature that go **beyond** the current PRD (FR-8.1 – FR-8.6), and separate *table-stakes* (what every credible app already does — absence is a defect) from *differentiators* (what almost nobody does — presence is an advantage).

**Research Type**: Market Research
**Date**: 2026-07-12

### Baseline: What We Already Ship (the floor this research must clear)

Research must produce ideas *beyond* this line. Anything below it is already built and is not a finding.

| Capability | Status |
| --- | --- |
| 5 deterministic detectors — post-payday spike, death-by-small-purchases, zombie subscriptions, weekend-vs-weekday pace, upcoming-commitment collision | Shipped (FR-8.1) |
| O→E→E→A narration (Observation → Explanation → Effect → Advice) | Shipped (FR-8.2) |
| Evidence block citing 2–3 exact data points (real dates, merchants, amounts) | Shipped (FR-8.2) — *closed 2026-07-12* |
| Severity tiers (critical / important / flexible) with ordering **and** visible badge | Shipped (Story 7.3) — *badge added 2026-07-12* |
| Dismiss → collapsed section; resurface only on ≥15% material metric change | Shipped (FR-8.4) — *collapsed section added 2026-07-12* |
| Empty state split: insufficient-data (<30 txns) vs. all-read | Shipped (FR-8.4) — *split added 2026-07-12* |
| "More data sharpens these patterns" footnote when `data_months < 3` | Shipped (FR-8.5) |
| "Ask the Copilot about this" handoff, insight-scoped | Shipped (Story 7.3 / 6.4) |
| Top insight woven into the daily briefing | Shipped (FR-8.6) |

### Hard Constraints Any Recommendation Must Respect

These are non-negotiable. A recommendation that violates one is not a finding, it is a bug.

1. **SEBI Investment-Adviser boundary.** Insights may invite the user to *consider* a change; they may **never prescribe**. Anything touching investments, equity, mutual funds or returns must carry "This is not investment advice." Enforced as a post-processor guard, not a per-narrator convention.
2. **No financial number originates in `services/narrate/`** (AD-1). Every figure an insight cites — including percentages, ratios and deltas — must be computed deterministically in `services/engine/` and passed in. This rules out any enhancement whose figures would be invented by an LLM.
3. **Honesty over engagement.** The product's stated posture is "patterns in your data — not judgments." Gamification/manipulation patterns common in this category (streaks, guilt-trip push, dark-pattern nudges) are a poor fit and must be flagged as such where competitors use them.
4. **Desktop-only, single-user MVP** (PRD X1). Mobile/push-notification-dependent mechanics are out of Phase-1 scope and must be labelled as such.
5. **WDS prototype is the UI source of truth.** Enhancements should extend the existing design system, not introduce a new one.

### Research Scope

**Competitors to analyse** (agreed set):

- **India:** Fi.Money, Jupiter, Walnut, CRED, (plus Paytm/PhonePe money-management surfaces where relevant)
- **Global:** Cleo, Monarch Money, Copilot Money, Emma, (plus the Mint diaspora — Credit Karma / Rocket Money / YNAB — as the category's historical baseline)

**Market Analysis Focus Areas:**

- Detection layer — what patterns competitors actually detect beyond our five
- Narration layer — how insights are worded, and who dares to be blunt vs. neutral
- Interaction layer — what a user can *do* with an insight (act, snooze, correct, teach, track)
- Trust layer — how apps prove an insight is true, and how they handle being wrong
- Regulatory layer — how India-based apps navigate the SEBI/RBI advice boundary

**Research Methodology:**

- Current web data with source verification
- Multiple independent sources for critical claims
- Confidence level assessment for uncertain data
- Explicit table-stakes vs. differentiator classification for every finding
- Every recommendation tested against the five hard constraints above

### Next Steps

**Research Workflow:**

1. ✅ Initialization and scope setting (current step)
2. Customer Insights and Behavior Analysis
3. Competitive Landscape Analysis
4. Strategic Synthesis and Recommendations

**Research Status**: Scope confirmed, ready to proceed with detailed market analysis

_Scope confirmed by user on 2026-07-12._

---

## Customer Behavior and Segments

### Customer Behavior Patterns

The defining behaviour in this category is **abandonment**, and it happens fast. Finance apps retain roughly **4.2% of users by day 30**, and the top-10 personal finance apps lose **71% of daily active users between Day 1 and Day 30** ([Business of Apps](https://www.businessofapps.com/data/finance-app-benchmarks/), [Branch](https://www.branch.io/resources/blog/3-proven-strategies-to-win-and-retain-finance-app-users/)). Among people who tried a budgeting app in the past year, **67% rated it "not helpful" or "too much effort to maintain"** ([Strategia-X](https://www.strategia-x.com/blog/2026-04-12-why-budgeting-apps-fail-30-days-fintech-ux-data/)).

The diagnosis in the literature is consistent, and it is *not* "insights were missing." It is that **tracking is not the same as changing behaviour, and most apps stop at tracking** ([Ritz Herald](https://ritzherald.com/why-most-personal-finance-apps-fail-to-change-behavior/)). In-app notifications and insights are "often overlooked, dismissed, or lost" ([Financial Fitness Passport](https://www.financialfitnesspassport.com/why-personal-finance-apps-fail-user-retention)).

_Behavior Drivers: avoidance of financial shame; low tolerance for maintenance effort; desire for guidance at the decision point, not a report after the fact._
_Interaction Preferences: personalised, timely, action-linked messages. Personalised notifications **tripled** weekly engagement to 13.5 sessions ([Pushwoosh](https://www.pushwoosh.com/blog/push-notifications-fintech/))._
_Decision Habits: users act on insights attached to a decision, and ignore insights attached to a summary._
_Confidence: HIGH — multiple independent sources agree on both the retention numbers and the diagnosis._

### 🔴 The Negative-Valence Trap (the most important behavioural finding)

> "The feedback loop is primarily negative: **users are informed when they are doing something wrong, not when they are doing something right.** Over time, this creates a Pavlovian association between opening the budgeting app and feeling bad about financial decisions — which predictably leads to app avoidance."
> — [Financial Fitness Passport](https://www.financialfitnesspassport.com/learn/why-budgeting-apps-fail-most-people)

**This finding indicts our current detector set directly.** Audit all five FR-8.1 detectors by emotional valence:

| Detector | Can it ever deliver good news? |
| --- | --- |
| Post-payday **spike** | ❌ Never — fires only on overspending |
| **Death** by small purchases | ❌ Never — the name is the verdict |
| **Zombie** subscriptions | ❌ Never — fires only on waste |
| Weekend-vs-weekday **pace** | ❌ Never — fires only above a 1.5× ratio |
| Upcoming commitment **collision** | ❌ Never — fires only on projected shortfall |

**Every insight this product can currently generate is bad news.** The feed is structurally incapable of telling a user they did well. A user who improves their behaviour — the app's entire purpose — is rewarded with an *empty feed*.

This is not a copy problem. It is a **detector-coverage** problem, and it is invisible in the PRD because FR-8.1 only ever asked for patterns worth *warning* about. It sits squarely against the product's own stated posture: a product that only ever notices your failures **is** judging you, whatever the subline says.

_Confidence: HIGH on the behavioural mechanism. The detector audit is a direct reading of `services/engine/insights/detectors.py`._

### Trust, Error, and the Missing Correction Loop

Trust in the insight layer is downstream of trust in the **categorisation** layer, and that is fragile: "transactions get miscategorized… instead of saving time, users end up fixing the app's mistakes," and "when categories feel wrong, **users question the reliability of the entire system**" ([Medium/Neculai](https://medium.com/@stefanneculai/why-most-budgeting-apps-fail-and-what-actually-works-88904191967e), [Financial Fitness Passport](https://www.financialfitnesspassport.com/learn/why-budgeting-apps-fail-most-people)).

The mechanism matters for us specifically: **an insight is a compounding bet on a category being right.** "Death by small purchases: ₹2,400 across 8 coffee runs" is *false* if three of those were reimbursed work expenses. Today the user's only response to a wrong insight is **Dismiss** — which teaches the system nothing, and under our own `≥15% material change` rule the same wrong insight resurfaces as soon as the metric moves. The user cannot say **"this is wrong"** as distinct from **"I've read this."**

The evidence block (shipped 2026-07-12) *raises* these stakes: we now show the exact merchants and dates behind a claim, which is precisely what lets a user notice the claim is wrong. Having invited the scrutiny, we offer no way to act on it.

_Confidence: HIGH — miscategorisation-erodes-trust is the most repeated theme in the budgeting-app critique literature._

### Demographic Segmentation (India)

The Indian competitor set has shifted materially and recently:

- **Fi.Money discontinued its neo-banking services in 2025–2026**, with **Jupiter growing in response** ([PaiseHelp](https://www.paisehelp.in/2026/03/jupiter-vs-fi-money-which-is-better.html), [Aayush Bhaskar](https://aayushbhaskar.com/fi-money-vs-jupiter-money/)). Fi is a **weakened** comparator, not the benchmark it was when this project's brief was written.
- **Jupiter** — "Spend Insights" auto-categorises debits into Dining/Shopping/Travel/Bills ([Jupiter](https://jupiter.money/money/)). This is **categorisation and reporting, not pattern detection**.
- **Walnut** — automatic expense tracking by **reading bank/payment SMS alerts**, no manual entry ([Decentro](https://decentro.tech/blog/best-money-saving-apps/)). Differentiator is *frictionless capture*, not insight.
- **CRED** — "CRED Money" offers **cash-flow insights** to a credit-score-750+ premium segment ([Decentro](https://decentro.tech/blog/best-money-saving-apps/)).

**Segment implication:** the Indian incumbents compete on **data capture and categorisation** and largely stop where our product *starts*. None ships a narrated, evidence-backed behavioural-pattern feed. The competitive threat is not from India — it is from the global cohort (Cleo, Copilot Money), whose most powerful mechanics are precisely the ones our regulatory position forbids.

_Confidence: MEDIUM-HIGH — feature descriptions come from vendor/marketing sources; the Fi.Money wind-down is corroborated by two independent sources._

### Behavior Drivers and Influences

_Emotional Drivers: shame-avoidance dominates. The app that makes you feel bad is the app you stop opening. Our "honesty without judgment" posture is a real asset — but only if the feed can also carry good news._
_Rational Drivers: users want the receipts. This is why the evidence block matters, and why it must be right._
_Social Influences: minimal in the India PFM context; no meaningful peer layer among the comparators._
_Economic Influences: subscription fatigue is real and well-understood by users — the zombie-subscription detector likely carries the highest immediate credibility of our five._
