# Feature Impact Analysis

> Which features best serve the prioritized personas and driving forces

**Document:** Trigger Map — Feature Impact
**Created:** 2026-07-07
**Status:** COMPLETE

---

## Scoring System

Each feature is scored by how strongly it serves each persona's driving forces, **weighted by persona priority** (the primary persona dominates the decision):

| Persona | Strong serve | Moderate serve | Weak/none |
|---|---|---|---|
| ⭐ Priya (PRIMARY) | **5** | **3** | **1** |
| 🚀 Rohan (SECONDARY) | 3 | 1 | 0 |
| 🌟 Kavya (TERTIARY) | 3 | 1 | 0 |

**Max possible score = 11** (5 + 3 + 3). The weighting is deliberate: a feature that delights Priya but ignores the others still outranks a feature that serves everyone moderately. **We design for the engine first.**

**Categories:** **Must Have** (MVP / WoZ — proves the engine) · **Consider** (fast-follow / depth) · **Defer** (later phase, real but not now).

---

## Feature Scoring Table

| Feature | ⭐ Priya | 🚀 Rohan | 🌟 Kavya | Total | Category |
|---|---|---|---|---|---|
| **Morning Safe-to-Spend briefing** (proactive, WhatsApp) | 5 | 3 | 1 | **9** | Must Have |
| **Honesty layer** (Confidence % + explicit uncertainty) | 5 | 3 | 3 | **11** | Must Have |
| **Conservative-by-default + ring-fenced commitments** | 5 | 3 | 1 | **9** | Must Have |
| **Gut-check copilot** (2-tap purchase decisions) | 5 | 1 | 0 | **6** | Must Have |
| **Financial Confidence Score** (preparedness, 0-100) | 5 | 3 | 1 | **9** | Must Have |
| **Non-judgmental tone system** (calm, observation-not-verdict) | 5 | 1 | 1 | **7** | Must Have |
| **Trust-first onboarding** (credentials + "what we don't share") | 5 | 3 | 3 | **11** | Must Have |
| **Multi-source ingestion** (manual / CSV/PDF / receipt + AA) | 5 | 3 | 1 | **9** | Must Have |
| **AI-narrated plain-language AA consent screen** | 5 | 1 | 3 | **9** | Must Have |
| **Financial Timeline** (90-day forward "Google Maps for money") | 3 | 3 | 0 | **6** | Consider |
| **Behavioral Pattern Engine** (monthly report) | 3 | 1 | 0 | **4** | Consider |
| **Financial Guardian** (proactive never-critical intervention) | 3 | 3 | 1 | **7** | Consider |
| **Shared Confidence Score + multi-account aggregation** (couples) | 1 | 3 | 1 | **5** | Consider |
| **Variable-income / freelancer mode** | 1 | 0 | 0 | **1** | Defer |
| **Employer aggregate outcome reporting** (B2B2C) | 1 | 0 | 3 | **4** | Defer |
| **Native app: biometric lock, lock-screen Confidence widget** | 3 | 1 | 0 | **4** | Defer |
| **Vernacular / multi-script statement parsing** | 3 | 1 | 0 | **4** | Defer* |

\* *Vernacular scores modestly against the current Priya profile but carries strategic GTM weight (vernacular-first launches structurally outperform retrofits) — a candidate to pull earlier than a pure score suggests. Flagged, not buried.*

---

## Must Have (MVP / Wizard-of-Oz — proves THE ENGINE)

These features exist to answer the only question that matters at this stage: *does Priya's anxiety measurably drop?*

- **Morning Safe-to-Spend briefing** → serves Priya's *daily-calm-without-effort* want and *end-of-month-shock* fear. The product's heartbeat.
- **Honesty layer (Confidence %)** → serves the *being-lied-to* fear for Priya AND Rohan's *rigor* need AND Kavya's *liability* fear — the only 11/11 alongside trust onboarding. The moat, literally scored.
- **Conservative-by-default + ring-fencing** → serves the *led-into-harm* fear; the non-negotiable safety guarantee behind the kill signal.
- **Gut-check copilot** → serves Priya's *decide-without-second-guessing* want and *paralysis* pain.
- **Confidence Score** → serves Priya's *feel-capable* want; the preparedness metric that trends up.
- **Non-judgmental tone system** → serves the *being-judged* fear; the emotional-safety half of the moat.
- **Trust-first onboarding + plain-language AA consent** → serves the credentials→security trust order all three personas share; without it, Priya never reaches the Safe-to-Spend pitch.
- **Multi-source ingestion** → load-bearing because only ~38% of borrowers are AA-enabled; an AA-only MVP excludes most of the market.

## Consider (fast-follow / depth, once the engine is proven)

- **Financial Timeline** → deepens the *upcoming-expenses* answer for Priya and gives Rohan goal-pace visibility.
- **Behavioral Pattern Engine** → adds explanatory depth; a Paid-tier value driver, not a habit-former.
- **Financial Guardian** → serves Rohan's *single-point-of-failure* relief; proactive intervention layered on the safety base.
- **Shared Confidence Score / aggregation** → the concrete reason a couple upgrades to Premium (Rohan) — Phase 3.

## Defer (real, but not now — guarding the Priya focus)

- **Variable-income / freelancer mode** → explicitly out of Phase 1 (irregular income breaks Safe-to-Spend reliability).
- **Employer aggregate reporting** → the Year-2 Kavya amplifier; building it now dilutes the engine.
- **Native-app-only features** → wait until WhatsApp proves the daily habit; don't build the native app first.
- **Vernacular parsing** → deferred by score but flagged for possible early pull-in on GTM grounds.

---

## Strategic Rationale

The scoring makes the strategy visible: **the two perfect-11 features are the honesty layer and trust-first onboarding** — not a flashy hero feature. That is the whole thesis. This product wins on *being trusted*, and both trust features serve all three personas at once, which is exactly why they can't be deprioritized.

Every Must-Have ties to a **primary-persona driver** (Priya scores 5 on all of them). Nothing reaches MVP on the strength of a secondary or tertiary persona alone — that discipline is what keeps the engine from being diluted. Rohan's and Kavya's strongest features (Shared Score, employer reporting) correctly land in Consider/Defer: real, valuable, and *later*.

**Connection to business goals:** the Must-Have set is precisely the WoZ feature set needed to test the ⭐ engine objective (anxiety reduction + Safe-to-Spend comprehension). The Consider set drives the 🚀 growth objectives (depth → conversion; couples → Premium). The Defer set unlocks the 🌟 ecosystem objectives (employer channel; diversification) — sequenced, never simultaneous.

---

## Development Phases (aligned with the Flywheel)

- **Phase 1 — Prove the engine (WoZ):** all Must-Have features → validate anxiety drop.
- **Phase 2 — Depth (native app):** Timeline, Pattern Engine, Guardian → retention & conversion.
- **Phase 3 — Household:** Shared Confidence Score + aggregation → Premium (Rohan).
- **Phase 4 — Employer channel (Year 2):** aggregate outcome reporting → B2B2C (Kavya).
- **Phase 5 — Diversification & vernacular:** revenue beyond subscription; vernacular-first reach.

---

## Related Documents

- **[trigger-map.md](trigger-map.md)** — Visual overview and navigation
- **[01-business-goals.md](01-business-goals.md)** — Objectives and metrics
- **[personas/02-priya-the-overwhelmed-earner.md](personas/02-priya-the-overwhelmed-earner.md)** — Primary persona
- **[personas/03-rohan-the-money-managing-partner.md](personas/03-rohan-the-money-managing-partner.md)** — Secondary persona
- **[personas/04-kavya-the-wellness-sponsor.md](personas/04-kavya-the-wellness-sponsor.md)** — Tertiary persona
- **[05-key-insights.md](05-key-insights.md)** — Strategic implications

---

_Back to [Trigger Map](trigger-map.md)_
