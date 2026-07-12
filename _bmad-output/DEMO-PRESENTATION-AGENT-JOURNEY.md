# AI-Powered Personal Finance Analyzer
## From Idea to Code — Agent & Workflow Journey
### Demo Presentation Document

> **Purpose:** Explain to the team every agent, skill, and workflow invoked to build this application from scratch — what each one did, when it was called, and why.

---

## The Big Picture

This application was built using the **BMAD (Build, Measure, and Deliver) methodology** combined with the **Whiteport Design Studio (WDS)** pipeline. Instead of coding first and asking questions later, the process was:

```
Idea → Research → Strategy → Design → Architecture → Build
```

Every step had a dedicated **AI agent** with a specific role. There were **two categories** of intelligence at work:

| Category | What it means |
|---|---|
| **BMAD/WDS Agents** | Specialist AI personas (strategists, designers, researchers, engineers) invoked by slash commands to produce planning artifacts |
| **Claude Code (implementation)** | The actual code-writing agent that executed each developer story |

---

## Phase 1 — Foundation (Day 0)
### Steps 1–6

---

### Step 1 — BMAD Framework Installation
**What happened:** The BMAD skill library was installed into the repository. This is the "toolbox" — all subsequent agent personas, workflow scripts, and output templates live here.

- **Agent:** Bootstrap script (no persona)
- **Output:** `.claude/skills/bmad-*` — the full BMAD skill library

---

### Step 2 — Brainstorming
**Slash command:** `bmad-brainstorming`
**Agent:** **Carson** — Elite Brainstorming Specialist

**Why invoked:** The product was only a rough concept ("personal finance analyzer"). Before writing any requirements, we needed structured divergent thinking.

**What Carson did:**
- Ran 3 brainstorming techniques: **Jobs To Be Done → How Might We → Build on What Works**
- Produced 37 ideas/decisions
- Defined the emotional core: *"transform financial confusion into financial confidence"*
- Coined the positioning: *"Every Rupee Already Has a Job — Your AI Is Managing It for You"*
- Established the **Trust Loop**: Prediction → Explanation → Recommendation → Outcome

**Output:** `brainstorm-intent.md`, `brainstorm.html`

---

### Step 3 — Design Thinking
**Slash command:** `bmad-cis-design-thinking`
**Agent:** **ALPHA** — Design Thinking Coach

**Why invoked:** Carson gave us a creator's perspective. ALPHA gave us the *user's* perspective before writing requirements.

**What ALPHA did:**
- Ran the Stanford d.school 5-phase process (Empathize → Define → Ideate → Prototype → Test)
- Created the primary persona: **Priya, 32** — salaried professional in Bangalore, financially anxious
- Built an empathy map (what Priya says, thinks, does, feels)
- Produced the Point-of-View statement: *"Priya needs a trusted AI companion that speaks first, not a dashboard that waits to be consulted — because her anxiety isn't caused by lack of data, it's caused by lack of a calm, honest voice."*
- Key insight: **The real competitor is avoidance, not other finance apps**

**Output:** `design-thinking-2026-07-07.md`

---

### Step 4 — Innovation Strategy
**Slash command:** `bmad-cis-innovation-strategy`
**Agent:** **ALPHA** — Innovation Strategist

**Why invoked:** After understanding the user, we needed the business model, market sizing, and competitive positioning.

**What ALPHA did:**
- TAM/SAM/SOM sizing for India's personal finance market
- Competitive landscape mapping (axio, Jupiter, Fi Money, ET Money, Cleo)
- Business model: **Freemium → ₹199/month → ₹499/month**
- Recommended **WhatsApp-first, no native app** for Phase 1
- Defined 3 strategic options, selected the consumer-first path
- Flagged a **18-month founding window** before incumbents can copy the core

**Output:** `innovation-strategy-2026-07-07.md`

---

### Step 5 — Problem Solving (Safe-to-Spend Formula Design)
**Slash command:** `bmad-cis-problem-solving`
**Agent:** **ALPHA** — Problem Solver

**Why invoked:** Two critical design questions were unresolved: *"How exactly should Safe-to-Spend be calculated?"* and *"How should the Confidence Score behave?"* These were too high-risk to leave as assumptions in a PRD.

**What ALPHA did:**
- Root-cause analysis for both problems
- Decided: **Confidence Score and Prediction Confidence are separate indicators** (not the same thing)
- Designed the **adaptive proximity window**: critical commitments reserved 7 days before due, important 5 days, flexible 3 days
- Rule: every Confidence Score change must be causally bound to a specific event — no silent unexplained score changes

**Output:** `problem-solution-2026-07-07.md`

---

## Phase 2 — Research (Days 1–2)
### Steps 7–8

---

### Step 7 — Market Research
**Slash command:** `bmad-market-research`
**Agent:** **ALPHA** — Market Researcher

**Why invoked:** All prior sessions rested on internally-derived market assumptions. Before writing a PRD, those needed external validation.

**What ALPHA did:**
- ~22 live web searches across customer behavior, competitors, and regulations
- **Validated the Priya persona** with real data: 68% app abandonment rate, 4.2% Day-30 retention in the category
- Found: 54% of Indian employees live paycheck-to-paycheck 3+ months
- **Competitive update:** Fi Money winding down banking services (March 2026) — the market had moved since Step 4
- **Regulatory flag:** SEBI's Investment Adviser framework applies to AI-driven advisory tools — the product must say "information," never "advice"
- Corrected optimistic assumptions: India/SEA freemium conversion is typically 1–5%, not the 5%+ originally assumed

**Output:** `market-personal-finance-copilot-market-india-research-2026-07-07.md`

---

### Step 8 — Domain Research
**Slash command:** `/bmad-domain-research`
**Agent:** **ALPHA** — Domain Research Facilitator (running parallel to Step 7 in a different session)

**Why invoked:** An independent validation pass on the same claims, approaching from a different angle (industry/technology focus rather than customer/market focus).

**What ALPHA did:**
- Corrected the competitor list: **Walnut no longer exists** — it merged into axio
- Found Jupiter (neobank, $186–201M funded) already markets AI budgeting — a much closer threat
- Cleo (global) already ships an agentic "Autopilot" — undercuts the 18-month window assumption
- Confirmed the AA framework real-world adoption is only ~38% of borrowers
- Both Steps 7 and 8 independently surfaced the same ~4.2% retention figure from different sources — strong corroboration

**Output:** `domain-ai-driven-personal-finance-management-apps-india-research-2026-07-07.md`

---

## Phase 3 — Product Definition (Day 2)
### Steps 9–16

---

### Step 9 — Process Governance Automation
**What happened:** A Claude Code stop-hook was added to `.claude/settings.json` that blocks the session from ending if `_bmad-output/` files changed but `PROJECT-PROGRESS.md` was not updated. This enforces the audit trail automatically.

- **Agent:** Claude Code (Process Historian)
- **Output:** `.claude/settings.json` (project-level stop hook)

---

### Step 10 — Product Brief (WDS Phase 1)
**Slash command:** `/wds-1-project-brief`
**Agent:** **Saga** — Strategic Business Analyst (Whiteport Design Studio persona)

**Why invoked:** First step of the WDS design pipeline. This is the "single source of truth" strategic document all subsequent design/build work points back to.

**What Saga did:**
- Read all 6 prior artifacts in full and synthesized them into one Complete Brief
- Hardened the regulatory framing: SEBI IA boundary = hard legal prerequisite
- Named multi-source data ingestion as **load-bearing MVP infrastructure**, not a v2 nicety
- Reframed ₹199/₹499 pricing and 40% D30 retention as **hypotheses**, not settled figures
- Corrected the competitor list with Steps 7/8 findings

**Output:** `A-Product-Brief/project-brief.md`, `_progress/00-design-log.md`

---

### Step 11 — Trigger Mapping (WDS Phase 2)
**Slash command:** `/wds-2-trigger-mapping`
**Agent:** **Saga** — Strategic Analyst (Dream Mode — autonomous generation)

**Why invoked:** WDS Phase 2 maps business goals to user psychology. It answers "what must this product trigger in the user?" before designing any screen.

**What Saga did:**
- Defined **3 target groups** (personas with business weight):
  - ⭐ **Priya** — The Overwhelmed Earner (PRIMARY / THE ENGINE)
  - 🚀 **Rohan** — The Money-Managing Partner (SECONDARY, household multiplier)
  - 🌟 **Kavya** — The Workplace Wellness Sponsor (TERTIARY, B2B2C Year-2 only)
- Weighted every feature by persona impact (5/3/1 scoring)
- The **honesty layer** and **trust-first onboarding** scored a perfect 11/11 — serves all three personas, encodes the product's moat

**Output:** 7 files under `B-Trigger-Map/` including business goals, 3 persona docs, key insights, feature impact analysis

---

### Step 12 — Technical Research
**Slash command:** `/bmad-technical-research`
**Agent:** **ALPHA** — Technology Stack Analyst → Systems Architect

**Why invoked:** The brainstorming session had explicitly deferred the concrete technical architecture. Before writing a PRD and coding, the stack needed to be verified against real constraints.

**What ALPHA did:**
- User mid-session re-scoped the target: **3-day locally-run MVP**, not a production cloud app
- Recommended stack: **Python 3.11 + Reflex + SQLite + pdfplumber/camelot + Claude claude-opus-4-8**
- Load-bearing decision: **deterministic engine** (Safe-to-Spend, Confidence Score) strictly separated from **LLM narration layer** — the AI explains numbers, never computes them
- Mid-session framework switch: user chose **Reflex** over Streamlit for full UI control

**Output:** `technical-ai-financial-copilot-mvp-technical-architecture-stack-research-2026-07-07.md`

---

### Step 13 — PRD + Epics & Stories (Build Handoff)
**Agent:** Claude Code (build-handoff author, direct synthesis)

**Why invoked:** After technical research was approved, the developer needed a formal requirements document and a prioritized backlog.

**What was produced:**
- **`prd.md`** — 9 MVP capabilities → FR-1 through FR-9 with acceptance criteria, NFRs, data model, success metrics
- **`epics-and-stories.md`** — E1–E9, story IDs mapped to FRs, day-by-day build order, scope-guard cut order
- Honesty/safety stories marked as **never-cut** (the engine + its pytest suite can never be dropped)

**Output:** `planning-artifacts/prd.md`, `planning-artifacts/epics-and-stories.md`

---

### Steps 14–16 — UX Scenarios (WDS Phase 3) + Scope Decisions
**Slash command:** `/wds-3-scenarios` + `/bmad-party-mode`
**Agents:** Claude Code (UX Scenario Facilitator) + Party Mode cast

**What happened:**
- 3 UX scenarios built as linear sunshine-path flows across 7 MVP pages
- **Party Mode** invoked to check whether scenarios matched the PRD scope
  - Cast: John (PM), Sally (UX), Murat (Test Architect), Amelia (Dev), Winston (Architect)
  - Found: Scenario 01 was marking "success" on a demo-stretch feature, not the real golden path
  - 3 critical fixes applied
- User then **promoted AI Insights + Copilot from demo-stretch to must-ship** — retiring the cut-line entirely

**Output:** `C-UX-Scenarios/00-ux-scenarios.md`, 3 scenario folders with page-step specs

---

## Phase 4 — UX Design & Prototyping (Day 2–3)
### Steps 17–22

---

### Steps 17–19 — UX Design (WDS Phase 4)
**Slash command:** `/wds-4-ux-design` (Dream Mode)
**Agent:** **Freya** — WDS Phase 4 UX Designer

**Why invoked:** WDS Phase 4 converts the scenario outlines into detailed page specifications — layout, components, interaction rules, accessibility requirements.

**What Freya did:**
- Designed all 7 MVP pages: Register, Login, Upload, Transactions, Dashboard, Commitments, Copilot
- Applied the brand's design language (WDS `.wds.css` theme)
- Specified every component: safe-to-spend hero card, confidence chip, commitment timeline, AI copilot chat
- Step 19: restructured the scenario tree when user decided Login should move to Scenario 01

**Output:** 9 page specification files under `C-UX-Scenarios/`

---

### Steps 20–22 — Prototyping (WDS Phase 5)
**Slash command:** `/wds-5-agentic-development`
**Agent:** Claude Code (WDS Phase 5 Implementation Partner)

**Why invoked:** Before writing real application code, a clickable HTML prototype was built to validate the UX design and serve as the visual reference for the Reflex implementation.

**What was built:**
- 7 HTML prototype views with shared CSS/JS (`wds.css`, `auth.js`)
- `demo-data.json` — 24 sample transactions used throughout development
- Auth flow: register → login → upload → dashboard sequence fully wired
- All flows verified: 24/24 Chrome DevTools Protocol checks passed, 0 console errors

**Output:** `prototypes/01-priyas-first-honest-morning-Prototype/` (7 HTML files + shared assets + README + HANDOFF.md)

---

## Phase 5 — Architecture, Validation & Governance (Day 3)
### Steps 23–26

---

### Step 23 — PRD Update (Incorporating UX Design + Prototype)
**Slash command:** `/bmad-prd` (Update mode)
**Agent:** Claude Code (bmad-prd Update facilitator)

Updated the PRD with: 9 FRs expanded from prototype learnings, §8 API Surface section added, 2 new NFRs (accessibility + streaming), all open items reconciled.

---

### Step 24 — Architecture Spine
**Slash command:** `/bmad-architecture`
**Agent:** Claude Code (Architecture facilitator)

Produced `ARCHITECTURE-SPINE.md` — **14 Architecture Decisions (ADs)** that govern every implementation choice:

| AD | Rule |
|---|---|
| AD-1 | The LLM never computes a number — engine is deterministic Python |
| AD-2 | Services layer is framework-agnostic (no Reflex imports in `services/`) |
| AD-4 | Every DB query filtered by `user_id` — no IDOR possible |
| AD-5 | Passwords bcrypt-hashed; tokens are UUIDs in HttpOnly cookies |
| AD-7 | LLM categorization output stored with provenance + confidence per row |
| AD-8 | All money arithmetic in `Decimal`, never `float` |
| AD-9 | Every Confidence Score change must be causally bound to a trigger event |
| AD-12 | All error paths return typed exceptions — no bare `Exception` to the UI |

---

### Step 25 — PRD + Architecture Validation (Two Parallel Subagents)
**Slash command:** `/bmad-validate-prd`
**Agents:** 2 parallel subagents — **Rubric Walker** + **Cross-Document Consistency Checker**

**What they did:**
- Rubric Walker: 7-dimension quality review → 22 findings (3 critical, 7 high, 7 medium, 5 low)
- Consistency Checker: paired-document audit across PRD × Epics × Scenarios × UX Spec × Architecture → 20 findings
- **17 fixes applied** across 5 documents before development started

---

### Step 26 — Generate Project Context (Agent-Facing Rules File)
**Slash command:** `/bmad-generate-project-context`
**Sub-skills invoked:** `/bmad-party-mode` (Code Review Crew) + `/bmad-advanced-elicitation`
**Agent:** Claude Code (Project Context facilitator) + Code Review Crew (Vex, Grumbal, Boundary, Yui, Dana)

**Why invoked:** Every dev agent that would implement a story needed a single "rules of the road" file to read before touching code. Without it, independently-dispatched agents would make different interpretations of the same ADs.

**What was produced:**
- `project-context.md` — **40 rules** across 9 categories
- Party Mode (Code Review Crew) surfaced **4 "Seams"** the architecture spine missed: divide-by-zero guard on the Safe-to-Spend formula, SSE streaming cleanup, dedup key normalization, untrusted DB text as LLM input
- Advanced Elicitation (Inversion + Failure Mode analysis) surfaced **6 "Agent-Misread Guards"**: `Decimal` not `float` for money, no derived math in the narrate layer, `user_id` on all user-scoped tables, etc.

---

## Phase 6 — Development (Days 3–7)
### Steps 27–62b

Development was organized into **8 Epics**, each containing multiple stories. Each story followed the same pipeline:

```
Create Story (context file) → Dev Story (implement) → Code Review (adversarial)
```

---

### Sprint Planning
**Slash command:** `bmad-sprint-planning` (via Amelia)
**Agent:** **Amelia** — Senior Software Engineer (`bmad-agent-dev`)

Amelia activated as the dev menu host, ran sprint planning, and sequenced the stories.

---

### Epic 1 — Auth & App Shell

| Story | What was built |
|---|---|
| 1.1 | Reflex app skeleton + SQLite DB + WDS theme wired |
| 1.2 | User registration with bcrypt + HttpOnly cookie |
| 1.3 | Login + auth guards on every protected route |
| 1.4 | Logout + token rotation + IDOR-hardened tests |
| 1.5 | Blur-time validation + aria-live registration success |

Code reviewer (inline adversarial): **Blind Hunter + Edge Case Hunter + Acceptance Auditor** (3 parallel subagents)

---

### Epic 2 — Statement Upload & Ingestion

| Story | What was built |
|---|---|
| 2.1 | Canonical `Transaction` model + `StatementParser` protocol |
| 2.2 | CSV parser (HDFC/SBI format) + dedup key + typed `IngestionError` |
| 2.3 | PDF parser chain: statementsparser → pdfplumber → camelot fallback |
| 2.4 | Upload page UI (Reflex) + dispatcher wiring real parser into the flow |
| 2.5 | Dedup + persistence — completes the Epic 2 pipeline |

Each story was code-reviewed. Notable fixes:
- `0.00`-padded debit/credit columns were silently rejecting valid rows → patched
- `map_table` was misaligning columns when a header cell was empty → patched
- Non-UTF-8 CSVs (cp1252, common in Indian bank exports) were crashing → added cp1252 → latin-1 fallback
- DB persist errors were escaping untyped to the UI → wrapped with typed `IngestionError`

---

### Epic 3 — Transaction Categorization

| Story | What was built |
|---|---|
| 3.1 | Tier-1 Rules Engine (deterministic merchant/keyword rules) + Transactions page |
| 3.2 | Tier-2 LLM Categorizer (Claude Haiku, batched `messages.parse()`, `cache_control: ephemeral`) |

**First LLM integration in the codebase.** The Tier-2 categorizer runs only on transactions that Tier-1 rules could not match. Results stored with provenance + confidence (AD-7). Graceful fallback if the API call fails — the app never breaks due to an LLM error.

Code review for 3.1 used **3 parallel subagents**: Blind Hunter, Edge Case Hunter, Acceptance Auditor.

---

### Epic 4 — Safe-to-Spend Engine
The deterministic financial calculation engine — the core of the product.

**What was built:**
- `services/engine/safe_to_spend.py` — the formula: `max(0, (balance − reserved − buffer) ÷ days)`, floored to nearest ₹10, rounded **down** (never up)
- `services/engine/inputs.py` — resolves stored `due_day` integers to real calendar dates, detects income from transaction history
- `services/engine/confidence_score.py` — the 0–100 score, event-driven, with every delta causally bound to a trigger (AD-9)

---

### Epic 5 — Dashboard + Commitments

| Story | What was built |
|---|---|
| 5.1 | Dashboard hero card (Safe-to-Spend, label-only confidence chip, briefing) |
| 5.2 | Confidence score drill-in panel |
| 5.3 | O→E→E→A briefing (Observation → Evidence → Explanation → Action) via LLM narration layer |
| 5.5 | Dedicated Commitments page with live engine-computed impact bar |

Key discipline: the `narrate/` layer **never imports from `engine/`** (AD-1). The engine runs first, then narration describes the result.

---

### Epic 6 — AI Copilot (NL Q&A)

Conversational AI interface where Priya can ask natural-language questions about her finances. The copilot uses **read-only tool calls** — it can query the database but cannot write anything. Streaming responses for real-time feel.

---

### Epic 7 — Insights & Recommendations

Proactive AI-generated insights surfaced on a dedicated Insights page. Detectors run against transaction history and fire when patterns are found (recurring charges, overspending categories, etc.). Minimum 3 detectors must fire for the MVP (never-cut floor set in validation Step 25).

---

### Epic 8 — Onboarding & Empty States

The first-run experience — what Priya sees before she has uploaded any data. Empty states for all 6 pages are designed to guide her to the next action rather than show a blank screen.

---

## All Agents — Quick Reference

| Agent | Type | Invoked By | What They Do |
|---|---|---|---|
| **Carson** | BMAD CIS persona | `bmad-brainstorming` | Divergent ideation — JTBD, How Might We, Build on What Works |
| **ALPHA** | BMAD research/strategy persona | Multiple skills | Design Thinking, Innovation Strategy, Problem Solving, Market Research, Domain Research, Technical Research |
| **Saga** | WDS Business Analyst | `/wds-1-project-brief`, `/wds-2-trigger-mapping` | Product Brief, Trigger Map, strategic foundation |
| **Freya** | WDS UX Designer | `/wds-4-ux-design` | Page specifications, component design, interaction rules |
| **Claude Code (WDS Phase 5)** | Implementation Partner | `/wds-5-agentic-development` | HTML prototypes |
| **Claude Code (Process Historian)** | Governance | Direct instruction | Maintains this audit trail, automation hooks |
| **Party Mode cast** | Multi-persona review | `/bmad-party-mode` | John (PM), Sally (UX), Murat (Test Architect), Amelia (Dev), Winston (Architect) — adversarial review panel |
| **Code Review Crew** | Adversarial reviewers | Nested in Step 26 | Vex, Grumbal, Boundary, Yui, Dana — architecture seam hunters |
| **Rubric Walker** | Validation subagent | `/bmad-validate-prd` | 7-dimension PRD quality review |
| **Consistency Checker** | Validation subagent | `/bmad-validate-prd` | Cross-document consistency audit |
| **Blind Hunter** | Code review subagent | `bmad-code-review` | Finds bugs the author would miss (no diff bias) |
| **Edge Case Hunter** | Code review subagent | `bmad-code-review` | Finds boundary conditions and off-by-one errors |
| **Acceptance Auditor** | Code review subagent | `bmad-code-review` | Verifies every acceptance criterion is actually met |
| **Amelia** | Senior Dev Engineer | `bmad-agent-dev` | Sprint planning, story creation, story implementation, code review |

---

## All Skills — In Order of First Use

| # | Skill | Phase | What it produces |
|---|---|---|---|
| 1 | `bmad-brainstorming` | Ideation | Product vision, emotional job, positioning |
| 2 | `bmad-cis-design-thinking` | User Research | Persona, empathy map, POV statement |
| 3 | `bmad-cis-innovation-strategy` | Strategy | Market sizing, business model, roadmap |
| 4 | `bmad-cis-problem-solving` | Design | Safe-to-Spend formula design, Confidence Score rules |
| 5 | `bmad-market-research` | Research | Market validation, competitor profiles, regulatory landscape |
| 6 | `bmad-domain-research` | Research | Domain/technology validation, competitor corrections |
| 7 | `wds-1-project-brief` | WDS Phase 1 | Strategic product brief (single source of truth) |
| 8 | `wds-2-trigger-mapping` | WDS Phase 2 | Business goals → user psychology map, persona weighting |
| 9 | `bmad-technical-research` | Architecture | Stack recommendation, 3-day build plan |
| 10 | `wds-3-scenarios` | WDS Phase 3 | UX scenario outlines (linear sunshine paths) |
| 11 | `bmad-party-mode` | Governance | Multi-persona adversarial review |
| 12 | `wds-4-ux-design` | WDS Phase 4 | Page specifications, component design |
| 13 | `wds-5-agentic-development` | WDS Phase 5 | HTML prototypes |
| 14 | `bmad-prd` | Requirements | PRD update + finalization |
| 15 | `bmad-architecture` | Architecture | ARCHITECTURE-SPINE.md (14 ADs) |
| 16 | `bmad-validate-prd` | Validation | Quality review + cross-document consistency |
| 17 | `bmad-generate-project-context` | Agent Enablement | Agent-facing rules file (40 rules) |
| 18 | `bmad-advanced-elicitation` | Governance | Inversion + failure mode analysis |
| 19 | `bmad-agent-pm` | Planning | PM-persona facilitation |
| 20 | `bmad-create-epics-and-stories` | Planning | Epic + story backlog |
| 21 | `bmad-check-implementation-readiness` | Validation | Build-readiness audit (72 FRs traced) |
| 22 | `bmad-sprint-planning` | Development | Sprint plan + story sequencing |
| 23 | `bmad-create-story` | Development | Per-story context file (5× used) |
| 24 | `bmad-dev-story` | Development | Story implementation (5× used) |
| 25 | `bmad-code-review` | Development | Adversarial 3-layer code review (5× used) |

---

## Key Architectural Decisions (for the demo)

| Decision | What it means in practice |
|---|---|
| **LLM never computes a number** | The Safe-to-Spend and Confidence Score are pure Python math. The AI only writes the sentence that explains the result. |
| **Deterministic engine = testable** | Every Safe-to-Spend scenario (13 scenarios covering edge cases) has a pytest assertion. The math is verifiable. |
| **Decimal, not float** | All money arithmetic uses Python's `Decimal` type. `float` is display-only. |
| **Every score delta has a cause** | The Confidence Score cannot change without a named trigger event (upload, commitment added, etc.). No mystery score jumps. |
| **Commitments ring-fence money** | Bills due before payday are subtracted from your spendable pool. The engine decides what to ring-fence; the LLM never touches that math. |
| **Read-only AI Copilot** | The copilot can query your data and explain it, but it cannot write, delete, or modify anything. |

---

## Stats

| Metric | Count |
|---|---|
| Total BMAD steps logged | 62+ |
| Distinct agent personas invoked | 15+ |
| Distinct skills used | 25 |
| Architecture Decisions (ADs) | 14 |
| Agent-facing rules in project-context.md | 40 |
| Functional Requirements (FRs) | FR-1 to FR-9 (72 traced sub-requirements) |
| Epics | 8 |
| Stories implemented | 20+ |
| pytest tests at last green run | 424+ |
| Safe-to-Spend test scenarios | 13 |
| Planning artifacts produced | 30+ markdown documents |
| Code reviews (adversarial) | 5 formal + multiple inline |

---

*Document generated from `PROJECT-PROGRESS.md` audit trail — all entries marked Observed (directly witnessed this session) or Inferred (reconstructed from git history + artifacts).*
