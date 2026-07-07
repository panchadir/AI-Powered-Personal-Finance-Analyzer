# Trigger Map → UX Design Handover

> Phase 2 (Trigger Mapping) → Phase 3 (UX Scenarios / UX Design) handover package

**Document:** Trigger Map — Handover to UX
**Created:** 2026-07-07
**From:** Saga (Strategic Analyst)
**To:** Freya (UX Designer) / Phase 3
**Status:** COMPLETE — Phase 2 wrapped

---

## Documentation Created

```
B-Trigger-Map/
  trigger-map.md              ← START HERE: visual overview + Mermaid diagram + navigation
  01-business-goals.md          Vision, SMART objectives (3 tiers), the flywheel, guardrails
  05-key-insights.md            Design implications, focus statement, phasing
  feature-impact-analysis.md    Persona-weighted feature scoring → Must/Consider/Defer
  handover-to-ux.md             ← THIS FILE
  personas/
    02-priya-the-overwhelmed-earner.md    ⭐ PRIMARY (THE ENGINE)
    03-rohan-the-money-managing-partner.md 🚀 SECONDARY (household / Premium)
    04-kavya-the-wellness-sponsor.md       🌟 TERTIARY (Year-2 employer sponsor)
```

---

## Primary Focus

- **Who:** ⭐ **Priya — The Overwhelmed Earner** (salaried, ~32, Mumbai, EMI-carrying; financially capable but emotionally overwhelmed; lives in WhatsApp).
- **Transformation:** from a money-avoider braced for the end-of-month shock → to a quietly confident person who *greets* a calm, honest morning briefing. Money becomes a companion who has her back, not a report card she's failing.
- **The real competitor is avoidance** — every design choice must make *looking* feel better than looking away.

## Must Address (Priya's positive drivers → deliver on these)
- ✅ **Daily calm without effort** → proactive WhatsApp Safe-to-Spend briefing; one number, one honest reason, zero homework.
- ✅ **Feel capable, not failing** → Confidence Score of *preparedness*, designed to trend up; observation, never verdict.
- ✅ **Decide purchases without regret** → 2-tap gut-check with reasoning attached.

## Must Avoid (Priya's negative drivers → neutralize these)
- ❌ **The end-of-month shock** → forward-looking briefing + Timeline; a heads-up, never a surprise.
- ❌ **Being judged (even by an app)** → non-judgmental, calm-not-alarmist tone; zero shame-adjacent language.
- ❌ **Being lied to / led into harm** → Confidence % + explicit uncertainty everywhere; conservative-by-default; ring-fenced commitments.

## Feature Priority (from feature-impact-analysis.md)
**Perfect 11/11 (serve all three personas — the moat):**
1. **Honesty layer** (Confidence % + explicit uncertainty)
2. **Trust-first onboarding** (credentials + "here's what we do NOT share")

**Other Must-Haves (MVP / WoZ):** morning Safe-to-Spend briefing · conservative-by-default + ring-fencing · gut-check copilot · Confidence Score · non-judgmental tone system · plain-language AA consent · multi-source ingestion.

**Consider (fast-follow):** Financial Timeline · Behavioral Pattern Engine · Financial Guardian · Shared Confidence Score (couples).

## Design Implications (top 3 for UX)
1. **The briefing IS the interface.** No dashboard on first launch — the WhatsApp thread / home screen is the morning Safe-to-Spend briefing. Radical simplicity: one number vs. committed spend, not multi-category charts.
2. **Honesty is a visible design element, not a disclaimer.** Confidence % and "what I don't know yet" must sit *with* the headline number, never buried below it. Freshness/latency shown, never hidden.
3. **Sequence trust before features.** Onboarding must lead with regulatory/data credentials and the "what we don't share" stance (Indian trust order: credentials → security → social proof → features), and reframe the AA consent screen in AI-narrated plain language.

---

## ⚠️ Open Items UX Should Know About

**Pending user confirmation (Dream mode did not elicit these interactively):**
- **Rohan** and **Kavya** personas are analyst-inferred extensions of the brief's secondary-user notes — confirm before deep UX work on their surfaces.

**Unresolved design questions carried from earlier phases (decisions still owed):**
- Confidence Score **cold-start** behavior (neutral 50 / data-based / hidden until threshold).
- **Data-latency** display (visible freshness indicator vs. silent use of last-known balance).
- **Multi-bank gap** handling (calculate-with-caveat vs. require all accounts connected).

**Hard constraints (non-negotiable in any design):**
- All copy is "information the user's own data shows," **never "advice"** (SEBI boundary).
- Safe-to-Spend can **never** recommend spending that causes a missed committed obligation (kill signal).
- Android budget-device first; WhatsApp-first, zero-install; conservative-by-default.

---

## Status

**✅ Phase 2: Trigger Mapping — COMPLETE.**
**→ Ready for Phase 3: UX Scenarios (`wds-3-scenarios`)** once Rohan/Kavya are confirmed.

---

## Related Documents

- **[trigger-map.md](trigger-map.md)** — Visual overview and navigation
- **[01-business-goals.md](01-business-goals.md)** — Objectives and metrics
- **[personas/02-priya-the-overwhelmed-earner.md](personas/02-priya-the-overwhelmed-earner.md)** — Primary persona
- **[05-key-insights.md](05-key-insights.md)** — Strategic implications
- **[feature-impact-analysis.md](feature-impact-analysis.md)** — Feature prioritization

---

_Back to [Trigger Map](trigger-map.md)_
