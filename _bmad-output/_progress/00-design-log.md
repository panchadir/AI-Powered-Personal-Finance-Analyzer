# Design Log

**Project:** AI-Powered-Personal-Finance-Analyzer
**Started:** 2026-07-07
**Method:** Whiteport Design Studio (WDS)

---

## Backlog

> Business-value items. Add links to detail files if needed.

- [x] Complete product brief — Phase 1
- [x] Define trigger map — Phase 2 (Dream mode; personas Rohan & Kavya pending user confirmation)
- [ ] Create user scenarios — Phase 3
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

---

## About This Folder

- **This file** — Single source of truth for project progress
- **agent-experiences/** — Compressed insights from design discussions (dated files)
- **wds-project-outline.yaml** — Project configuration from Phase 0 setup (not yet run for this project)
