# AI-Powered Personal Finance Analyzer — Project Progress Tracker

> **Auto-updated after each session or workflow completion.**
> Tracks: steps completed, artifacts produced, agents/skills invoked, and sub-steps within each session.

---

## Project Summary

**Product:** AI Financial Copilot that turns financial confusion into financial confidence.
**Positioning:** *"Every Rupee Already Has a Job — Your AI Is Managing It for You."*
**Core Design Challenge:** How do we design an AI Financial Copilot that meets users at their moment of financial anxiety with clarity, honesty, and zero manual effort?

---

## Overall Progress

```
[DONE] Phase 1 — BMAD Framework Setup
[DONE] Phase 2 — Ideation & Brainstorming
[PART] Phase 3 — Design Thinking  (Empathize + Define done; Ideate/Prototype/Test pending)
[DONE] Phase 4 — Innovation Strategy
[TODO] Phase 5 — Product Brief / PRD
[TODO] Phase 6 — Architecture & Technical Design
[TODO] Phase 7 — UX Design & Scenarios
[TODO] Phase 8 — Development
```

---

## Completed Steps

---

### Step 1 — BMAD Framework Setup

| | |
|---|---|
| **Date** | 2026-07-06 |
| **Commit** | `fab16de` |
| **Skill / Agent** | *(BMAD init — framework scaffolding)* |
| **Facilitator / Mode** | *(setup script)* |
| **Why this skill** | BMAD is the project methodology chosen to structure the entire product lifecycle — from brainstorming through to development. Setting up the framework first establishes the opinionated folder structure, config, and workflow conventions that every subsequent skill and agent depends on. Without this foundation, later skills would have no consistent place to write artifacts or read shared context. |

**What happened:** BMAD framework initialized in the project; full `_bmad/` directory structure created with config, agents, scripts, and workflow directories.

**Sub-steps executed:**

| # | Sub-step | Outcome |
|---|----------|---------|
| 1.1 | Initialize `_bmad/` directory structure | Complete |
| 1.2 | Create `config.toml` + `config.user.toml` | Complete |
| 1.3 | Scaffold `_bmad-output/` with subdirectories (brainstorming, planning-artifacts, implementation-artifacts, test-artifacts) | Complete |
| 1.4 | Scaffold `design-artifacts/` with stage folders (A–E) | Complete |

**Artifacts produced:**
- `_bmad/` — full BMAD framework directory
- `_bmad/config.toml`, `_bmad/config.user.toml`
- `_bmad-output/` subdirectory structure
- `design-artifacts/A-Product-Brief/`, `B-Trigger-Map/`, `C-UX-Scenarios/`, `D-Design-System/`, `E-Development/`

---

### Step 2 — Brainstorming Session

| | |
|---|---|
| **Date** | 2026-07-06 |
| **Commit** | `d6966a4` |
| **Skill / Agent** | `bmad-brainstorming` |
| **Facilitator / Mode** | **Carson** — Elite Brainstorming Specialist · *Creative Partner* mode |
| **Why this skill** | At this stage the product idea existed only as a rough concept ("personal finance analyzer"). Before writing any requirements or architecture, we needed divergent thinking — to explore the problem space broadly, challenge assumptions, and surface the emotional and behavioral dimensions that would define the product. `bmad-brainstorming` was chosen because it runs structured creative techniques (JTBD, HMW, competitive analysis) in a single session and converges to a clean `brainstorm-intent.md` that becomes a direct input to the PRD. Skipping this step would have meant building requirements on top of surface-level assumptions rather than a genuinely understood user problem. |

**What happened:** Full creative brainstorming session run on the product concept using 3 progressive lenses. Produced a rich product intent document capturing the vision, user personas, core features, and product pillars. Also produced an interactive HTML brainstorm visualization.

**Sub-steps executed:**

| # | Sub-step / Technique | Key Output |
|---|----------------------|-----------|
| 2.1 | **Lens 1 — Jobs To Be Done** | Identified the *emotional* job (anxiety → confidence), not the functional one. Mapped 3 time-horizon struggling moments: BEHIND (end-of-month shock) / NOW (payday uncertainty) / AHEAD (upcoming-expenses anxiety). |
| 2.2 | **Lens 1 (cont.) — Behavioral Mirror** | Uncovered 7 behavioral insight types: stress spending, death-by-small-purchases, post-payday spike, zombie subscriptions, the repeating cycle, "surprises aren't surprises," and missing buffer as the real risk. Each follows the pattern: Observation → Evidence → Explanation → Action. |
| 2.3 | **Lens 2 — How Might We** | Generated 4 core HMW questions spanning past→pattern→prediction→prescription. Developed 4 product concepts from them: AI Financial Copilot, Financial Confidence Score, Financial Timeline, Financial Guardian. |
| 2.4 | **Lens 2 (cont.) — Trust Loop & Moat** | Designed the Trust Loop mechanic (Prediction → Explanation → Recommendation → Outcome). Defined "Confidence with Humility" as the competitive moat — handling irregular income, missing data, variable bills, and low-confidence states honestly. |
| 2.5 | **Lens 3 — Build on What Works** | Competitive analysis: absorbed YNAB's "give every rupee a job" mindset shift, removed manual effort via AI. Produced the billboard positioning line. |
| 2.6 | **Lens 3 (cont.) — Data Strategy** | Defined multi-source data approach (bank API / CSV / receipt / cash / commitments). Established User Action → AI Learns → User Sees Benefit loop. Provenance transparency as trust-builder. |
| 2.7 | **Synthesis — Connections** | 4 cross-cutting connections identified tying moat, automation, Confidence Score, and failure-handling into one coherent product. 37 ideas & decisions captured total. |

**Artifacts produced:**
- [`_bmad-output/brainstorming/brainstorm-ai-powered-personal-finance-analyzer-2026-07-06/brainstorm.html`](_bmad-output/brainstorming/brainstorm-ai-powered-personal-finance-analyzer-2026-07-06/brainstorm.html) — interactive HTML keepsake
- [`_bmad-output/brainstorming/brainstorm-ai-powered-personal-finance-analyzer-2026-07-06/brainstorm-intent.md`](_bmad-output/brainstorming/brainstorm-ai-powered-personal-finance-analyzer-2026-07-06/brainstorm-intent.md) — **key product intent doc; direct input for PRD**
- [`_bmad-output/brainstorming/brainstorm-ai-powered-personal-finance-analyzer-2026-07-06/.memlog.md`](_bmad-output/brainstorming/brainstorm-ai-powered-personal-finance-analyzer-2026-07-06/.memlog.md) — full session decision log (46 entries)

---

### Step 3 — Design Thinking Session

| | |
|---|---|
| **Date** | 2026-07-07 |
| **Skill / Agent** | `bmad-cis-design-thinking` |
| **Facilitator / Mode** | **ALPHA** — Design Thinking Coach · *CIS (Creative Intelligence Suite)* mode |
| **Status** | Partial — phases 1–2 complete; phases 3–5 pending |
| **Why this skill** | The brainstorming session produced a rich vision but it was entirely creator-perspective — what *we* think the product should do. Before writing a PRD or designing any screen, we needed to deeply understand the *user's* perspective: their emotional state, the exact moments of frustration, and the real job they are hiring the product for. `bmad-cis-design-thinking` runs the Stanford d.school 5-phase process (Empathize → Define → Ideate → Prototype → Test) and forces every design decision to be anchored in observed user behaviour rather than assumed features. It was chosen specifically because it produces a structured Point of View statement and HMW questions that directly feed into ideation — bridging user insight to solution space in one coherent document. |

**What happened:** Full Design Thinking session initiated. Phases 1 (Empathize) and 2 (Define) completed in depth. Phases 3–5 (Ideate, Prototype, Test) are scaffolded in the output doc but not yet populated.

**Sub-steps executed:**

| # | Phase / Sub-step | Key Output |
|---|------------------|-----------|
| 3.1 | **EMPATHIZE — Persona Development** | Built primary persona: **Priya, 32** — salaried professional, Mumbai, some variable income, zero working budget system. |
| 3.2 | **EMPATHIZE — Says / Thinks / Does / Feels** | Full quadrant empathy map. Core finding: she avoids the app because it makes her feel *worse*, not better. Every bar chart of overspending is an accusation. |
| 3.3 | **EMPATHIZE — Key Observations** | 4 observations: (1) avoidance loop is the real product problem; (2) 3 predictable anxiety spikes; (3) she's hiring a *reassurance engine*, not a tracker; (4) trust is earned through honesty, not polish. |
| 3.4 | **DEFINE — Point of View Statement** | *"Priya needs a trusted AI companion that speaks first, not a dashboard that waits to be consulted — because her anxiety isn't caused by lack of data, it's caused by lack of a calm, honest voice."* |
| 3.5 | **DEFINE — How Might We (12 questions)** | 12 HMW questions across 4 themes: Avoidance Loop / Anxiety Spikes / Trust / Long Game. |
| 3.6 | **DEFINE — Key Insights (5)** | (1) Real competitor is avoidance, not Mint; (2) Confidence is the product, money management is the mechanism; (3) AI must speak first; (4) Honesty IS the moat; (5) The pattern is the superpower. |
| 3.7 | **IDEATE — Generate Solutions** | *(Scaffolded — pending next session)* |
| 3.8 | **PROTOTYPE — Make Ideas Tangible** | *(Scaffolded — pending next session)* |
| 3.9 | **TEST — Validate with Users** | *(Scaffolded — pending next session)* |

**Artifacts produced:**
- [`_bmad-output/design-thinking-2026-07-07.md`](_bmad-output/design-thinking-2026-07-07.md) — design thinking document (Ideate / Prototype / Test sections still TODO)

---

### Step 4 — Innovation Strategy Session

| | |
|---|---|
| **Date** | 2026-07-07 |
| **Skill / Agent** | `bmad-cis-innovation-strategy` |
| **Facilitator / Mode** | **ALPHA** — Innovation Strategist · *CIS (Creative Intelligence Suite)* mode |
| **Status** | Complete |
| **Why this skill** | After the brainstorming and design thinking sessions we had strong product intuition but no market, business, or strategic grounding. Before writing a PRD, we needed to answer: Who exactly is the market? Is there a real business here? What is the competitive moat and how defensible is it? What strategic path gives us the best chance of winning? `bmad-cis-innovation-strategy` was chosen because it runs a full market + competitive + business model + disruption analysis and forces a ranked strategic recommendation with an execution roadmap. This step also directly answered the monetization, market sizing, integration, and success metrics questions that were left open by the brainstorm — meaning the PRD now has a grounded strategic foundation to build on, not assumptions. |

**What happened:** Complete innovation strategy session covering market sizing, competitive positioning, business model design, disruption analysis, 3 strategic options evaluated, a recommended strategy with rationale, a 3-phase execution roadmap, success metrics with decision gates, and a risk register.

**Sub-steps executed:**

| # | Phase / Sub-step | Key Output |
|---|------------------|-----------|
| 4.1 | **Strategic Context** | Situation assessment: pre-product startup, rich validated insight from Sessions 2 & 3, founding window estimated at 12–18 months post-PMF before banks copy the morning briefing concept. |
| 4.2 | **Market Analysis — TAM/SAM/SOM** | TAM: ~180–200M financially-stressed salaried smartphone users in India. SAM: ~40–50M urban/semi-urban 25–40 age band. SOM (Year 1–2): 500K–2M early adopters (~1–4% of SAM). Revenue floor at SOM: ₹1Cr/month at 5% freemium conversion. |
| 4.3 | **Competitive Positioning** | Competitive map: X-axis = Emotional Safety, Y-axis = AI Intelligence. White space confirmed: High emotional safety + high AI intelligence — **unoccupied** by any current player. Five Forces analysis: bank copycat risk is the highest threat (18-month kill-clock). |
| 4.4 | **Business Model Design** | Freemium architecture: Free (morning briefing + Safe-to-Spend + basic Confidence Score) → Paid ₹199/month (full reasoning, gut-check copilot, pattern engine, timeline) → Premium ₹499/month (variable income, partners, annual review). Conversion trigger: the paywall moment is "I want to know *why* Safe-to-Spend is what it is." |
| 4.5 | **Disruption Opportunity Analysis** | 3 disruption vectors: (1) emotional accessibility winning non-consumers; (2) proactive push vs. passive pull — incumbents' UX debt makes rebuilding structurally costly; (3) honest uncertainty as a feature — incumbents can't admit they don't know without breaking their "always right" brand. Blue Ocean ERRC grid completed. |
| 4.6 | **Innovation Initiatives** | 8 initiatives ranked by horizon / impact / effort: H1 = Morning Briefing, Confidence Score, Gut-check Copilot, WhatsApp-first launch; H2 = Behavioral Pattern Engine, B2B2C corporate channel, Financial Timeline; H3 = Embedded financial actions. |
| 4.7 | **Strategic Options Evaluation** | 3 options built and scored against 5 criteria: (A) Consumer-first B2C — highest strategic fit + moat speed; (B) B2B2C corporate wellness first — highest revenue certainty; (C) Platform/API play — lowest strategic fit. |
| 4.8 | **Recommended Strategy** | **Option A as core + Option B as Year 2 amplifier.** Launch consumer-first, WhatsApp-first, zero-app-required. Use Wizard of Oz test as both validation and first-user acquisition. Add B2B2C corporate channel in Year 2 once PMF is proven. |
| 4.9 | **Execution Roadmap** | Phase 1 (Prove the briefing): Wizard of Oz test, tone guide, Safe-to-Spend formula v1, Confidence Score rubric, legal opinion, waitlist + referral loop, AA integration PoC. Gate: avg rating ≥ 3.5/5 to proceed. Phase 2 (Build the product): Native app, gut-check copilot, pattern engine v1, freemium paywall, referral engine. Gate: 10K active users + ≥5% paid conversion. Phase 3 (Scale): B2B2C channel, Financial Timeline, Premium tier, Pattern Engine v2, Hindi/regional languages. |
| 4.10 | **Success Metrics & Decision Gates** | 6 leading indicators (briefing open rate, gut-check frequency, AI corrections, Confidence Score trend, referral rate, self-reported anxiety reduction). 6 lagging indicators (D7/D30/D90 retention, free→paid conversion, churn, NPS, ARPU, LTV:CAC). 6 decision gates defined. |
| 4.11 | **Risks & Mitigation** | 6 risks with probability / impact / kill potential scored: bank copycat (High/High/Medium), AA data quality (Medium/High/Medium), regulatory reclassification (Medium/Critical/High), Safe-to-Spend error (Low/Critical/High), CAC > LTV (Medium/High/Medium), Confidence Score gimmicky (Medium/Medium/Low). Mitigation strategy for each. |

**Artifacts produced:**
- [`_bmad-output/innovation-strategy-2026-07-07.md`](_bmad-output/innovation-strategy-2026-07-07.md) — **complete innovation strategy; locked market, business model, strategic direction, roadmap, metrics, and risks**

---

## Pending / Next Steps

| Priority | Step | Skill/Agent to Use | Why this skill | Depends On |
|----------|------|--------------------|----------------|-----------|
| 1 | Complete Design Thinking — Ideate, Prototype, Test phases | `bmad-cis-design-thinking` | The Empathize + Define phases gave us the user problem and HMW questions. Ideate turns those HMW questions into concrete solution concepts; Prototype makes the best concepts tangible enough to test; Test validates assumptions before any PRD is written. All 5 phases must complete before the design thinking doc can reliably feed into the Product Brief. | Step 3 (partial) |
| 2 | Create Product Brief | `bmad-product-brief` | After four sessions of divergent exploration (brainstorm, design thinking, innovation strategy), the project needs a convergence step: a concise, opinionated brief that locks MVP scope, target user, positioning, and success metrics. `bmad-product-brief` produces a crisp 1–2 page strategic anchor that aligns all stakeholders before the detailed PRD is written — preventing scope creep and rework downstream. | Step 3 complete + Step 4 |
| 3 | Create PRD | `bmad-create-prd` | The Product Brief gives direction; the PRD translates that direction into precise, implementable requirements. `bmad-create-prd` structures requirements into epics and user stories with acceptance criteria, ensuring engineers and designers have an unambiguous contract to build against. This is the bridge between product strategy and execution. | Product Brief |
| 4 | Technical Architecture | `bmad-create-architecture` | The PRD defines *what* to build; architecture defines *how*. For an AI-heavy product (LLM, RAG, agents, cash-flow forecasting, behavioral pattern detection), architecture decisions are high-risk and high-cost to change later. `bmad-create-architecture` forces explicit decisions on model selection, data pipeline, agent design, AA framework integration, and WhatsApp delivery before a single line of production code is written. | PRD |
| 5 | UX Design & Scenarios | `bmad-ux` or `wds-4-ux-design` | This product lives or dies on its UX — the entire thesis is that users will open *this* app instead of looking away. `bmad-ux` / `wds-4-ux-design` translates the POV statement and HMW questions from design thinking into concrete wireframes, key screen flows, and interaction patterns. Running this after the PRD ensures UX is scoped to confirmed requirements, not an unconstrained wishlist. | PRD |
| 6 | WDS Trigger Mapping | `wds-2-trigger-mapping` | The AI must speak first — but *when* and *why*? Trigger mapping explicitly documents every user state or event (payday, overspend threshold, upcoming bill, purchase gut-check) that should cause the AI to proactively surface an insight. Without this step, proactive AI behaviour is left to developer interpretation, leading to inconsistent or intrusive patterns. | UX Design |
| 7 | WDS UX Scenarios | `wds-3-scenarios` | Trigger mapping defines *when* the AI acts; UX scenarios define *how* that moment looks and feels. `wds-3-scenarios` writes detailed narrative walkthroughs for each key trigger — what the user is doing, what the AI says, what happens next. These become the acceptance test scripts for the conversational AI layer and prevent the "technically correct but emotionally wrong" failure mode. | Trigger Map |
| 8 | Development Planning | `bmad-create-epics-and-stories` | Architecture and UX scenarios are still too coarse to assign to a sprint. `bmad-create-epics-and-stories` breaks the confirmed scope into sized, prioritized, dependency-ordered stories with clear acceptance criteria. This is the last step before development starts and is the primary handoff artefact between product and engineering. | Architecture + UX Scenarios |
| 9 | Development | `bmad-agent-dev` / `bmad-dev-story` | `bmad-dev-story` executes one user story at a time — reading the story, implementing the code, writing tests, and marking it done. `bmad-agent-dev` provides autonomous multi-story execution for larger implementation runs. These are invoked last because every upstream artefact (PRD, architecture, UX, stories) must be stable before coding begins to avoid rebuilding on shifting foundations. | Stories |

---

## Design Artifacts Directory

```
design-artifacts/
├── A-Product-Brief/          [EMPTY — not yet started]
├── B-Trigger-Map/            [EMPTY — not yet started]
├── C-UX-Scenarios/           [EMPTY — not yet started]
├── D-Design-System/          [EMPTY — not yet started]
└── E-Development/            [EMPTY — not yet started]
```

---

## All Agents & Skills Invoked (cumulative)

| # | Session Date | Skill / Agent | Facilitator | Purpose | Why chosen | Status |
|---|--------------|--------------|-------------|---------|------------|--------|
| 1 | 2026-07-06 | *(BMAD init)* | setup script | Framework scaffolding — establish folder structure, config, and workflow conventions for all subsequent skills | BMAD methodology chosen for the entire project lifecycle; foundation must exist before any skill can write structured output | Complete |
| 2 | 2026-07-06 | `bmad-brainstorming` | Carson (Creative Partner) | Creative brainstorming — 3 lenses (JTBD, HMW, Build on What Works), 37 ideas & decisions | Product was a rough concept; needed divergent creative exploration to surface the emotional problem space, user jobs, and competitive angles before writing any requirements | Complete |
| 3 | 2026-07-07 | `bmad-cis-design-thinking` | ALPHA (Design Thinking Coach) | Design Thinking — Empathize + Define phases (Ideate/Prototype/Test pending) | Brainstorm produced creator-perspective vision; needed user-perspective anchoring (persona, empathy map, POV statement, HMW questions) before any screen or requirement was defined | Partial |
| 4 | 2026-07-07 | `bmad-cis-innovation-strategy` | ALPHA (Innovation Strategist) | Full innovation strategy — market sizing, competitive map, business model, disruption vectors, 3 strategic options, recommended path, 3-phase roadmap, success metrics, risk register | After product clarity, needed market + business grounding before PRD; answered all deferred open questions (monetization, market size, integrations, success metrics, strategic direction) | Complete |
| 5 | 2026-07-07 | `bmad-cis-problem-solving` | ALPHA (Problem Solver) | Systematic problem-solving session for Safe-to-Spend formula design (Problem A) and Confidence Score design (Problem D) — two critical product design problems blocking MVP specification | These were the highest-risk unresolved product design questions from the innovation strategy session; solving them before writing the PRD prevents building requirements on top of unvalidated formula and scoring assumptions | Partial — Steps 1–3 complete, Step 4 in progress |

---

## Key Decisions Made

| # | Decision | Source Session |
|---|----------|---------------|
| 1 | **Emotional framing wins** — product is a *confidence engine*, not a budgeting app; anxiety reduction is the north star | Step 2 Brainstorm |
| 2 | **Financial Confidence Score is the product spine** — not just a feature; the number going up is the dopamine and retention loop | Step 2 Brainstorm |
| 3 | **Honesty is the moat** — "Confidence with Humility" (surfacing uncertainty %) is structurally uncopyable by competitors whose brand is "always right" | Step 2 Brainstorm |
| 4 | **AI speaks first** — proactive briefings, not dashboards waiting to be consulted | Step 2 Brainstorm |
| 5 | **Real competitor is avoidance, not Mint** — winning means being better than looking away | Step 3 Design Thinking |
| 6 | **Pattern detection is the superpower** — the AI sees behavioral cycles users are too close to notice themselves | Step 3 Design Thinking |
| 7 | **Go consumer-first, WhatsApp-first** — launch without a native app; prove the morning briefing creates a daily habit via WhatsApp before building the app | Step 4 Innovation Strategy |
| 8 | **Freemium at ₹199/month** — free tier builds habit; paywall moment is "I want to know *why*"; conversion target 5%+ at Day 30 | Step 4 Innovation Strategy |
| 9 | **Wizard of Oz test is Phase 1** — 5–7 users, 1 week of manual WhatsApp briefings to validate core hypothesis before any engineering investment | Step 4 Innovation Strategy |
| 10 | **B2B2C is Year 2 amplifier, not the launch path** — PMF must be proven on voluntary consumer adoption first; corporate distribution then pours accelerant on a burning fire | Step 4 Innovation Strategy |
| 11 | **18-month founding window** — AA framework + LLMs + UPI data richness converged in 2025–2026; banks can copy the briefing concept within 18 months of it being proven; depth of behavioral memory is the only moat they can't quickly replicate | Step 4 Innovation Strategy |
| 12 | **Two-indicator architecture** — Confidence Score (0–100, measures financial preparedness) and Prediction Confidence (Low/Medium/High, measures AI data completeness) are separate orthogonal indicators that must never be conflated | Step 5 Problem Solving |
| 13 | **Adaptive proximity window** — committed expenses ring-fenced from Safe-to-Spend starting 7 days before due date, with escalating conservatism; critical expenses (rent, EMI, insurance) weighted more heavily than minor commitments | Step 5 Problem Solving |
| 14 | **Event-to-explanation binding** — every Confidence Score delta is atomic with its cause; score and explanation cannot be architecturally decoupled; push notifications reserved for significant/actionable events only | Step 5 Problem Solving |
| 15 | **Confidence Score rewards financial readiness, not product usage** — engagement improves data quality (indirectly improving accuracy) but never artificially inflates the score | Step 5 Problem Solving |
| 16 | **Safe-to-Spend shows today's reality + confirmed future income as separate layer** — never presents anticipated income as available balance; distinguishes "Available Today" from "Available After Confirmed Income" | Step 5 Problem Solving |

---

## Open Questions

| Question | Status |
|----------|--------|
| What is the MVP feature cut vs. full vision? | **Answered (Step 4)** — Phase 1 MVP: morning briefing, Safe-to-Spend, basic Confidence Score via WhatsApp. Phase 2 app adds gut-check copilot, pattern engine, freemium paywall. |
| Monetization model? | **Answered (Step 4)** — Freemium: Free → ₹199/month (Paid) → ₹499/month (Premium) |
| Success metrics and KPIs? | **Answered (Step 4)** — 6 leading + 6 lagging indicators defined; 6 decision gates with pass/fail thresholds |
| Target integrations? | **Answered (Step 4)** — AA Aggregators (Finvu, OneMoney, Setu), UPI apps (PhonePe, GPay), WhatsApp Business API, HR platforms (Year 2) |
| Safe-to-Spend formula design? | **Partially answered (Step 5)** — root cause, boundaries, adaptive proximity window, and two-indicator architecture locked. Force field analysis started. 3 constraint questions open for next session (data latency handling, cold-start Confidence Score, multi-bank gap). |
| Confidence Score design? | **Partially answered (Step 5)** — measures preparedness not engagement; event-to-explanation binding required; notification tiering defined. Constraint questions and solution generation pending. |
| Specific LLM / RAG / agent architecture? | **Open** — to be resolved in Step 6 (Technical Architecture) |
| Security & privacy implementation? | **Open** — legal opinion on "financial information" vs. "financial advice" boundary needed before 10K users; to be resolved in Step 6 |

---

*Last updated: 2026-07-07 | Update this file after every session or workflow completion.*
