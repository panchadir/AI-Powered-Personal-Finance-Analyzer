---
title: "PRD Quality Review — AI-Powered Personal Finance Analyzer MVP"
created: 2026-07-08
reviewer: automated rubric pass
---

# PRD Quality Review — AI-Powered Personal Finance Analyzer MVP

## Overall verdict

The PRD's technical honesty spine is genuinely load-bearing and rigorously enforced — the deterministic-vs-LLM separation, the read-only Copilot tool constraint, and the engine-layer ACs are specific enough to gate a real build. However, for a consumer product built around a named persona, the complete absence of embedded User Journeys and a glossary creates concrete downstream risk: a developer creating stories from this PRD must synthesize across five or more external documents to understand what "done" looks like on any UX-layer requirement. The UX acceptance criteria routinely use subjective language ("calm, honest sentence," "graceful," "never accusation") that no engineer can deterministically verify without an independent spec — which is absent from this document.

---

## 1. Decision-readiness — adequate

The 2026-07-08 scope lock is explicit and the delivery-risk note (§2, "committing all eight capabilities in a 3-day solo build removes the previous stretch safety-margin") is one of the most honest sentences in any MVP PRD. The all-in decision is traceable to a named project-owner decision, which is the right provenance signal. Open items (§12) are genuine: X1 (responsive gap), O2 (commitments page vs. section) are unresolved and correctly flagged.

The cut order, however, is under-specified. §2 says "trim via the epics' scope-guard cut order (polish/quality first — the deterministic engine + honesty spine is never cut)" — but the cut sequence after polish is not listed. A decision-maker facing a Day-2 schedule slip cannot act on "cut polish first"; they need a ranked list of what gets deferred in what order. The epics document is referenced but not embedded or summarized, which makes this a pointer to an answer rather than an answer.

No budget, resourcing, or release-criteria framing beyond "solo build" and the <$15 API cost cap. No explicit threshold for what constitutes a failed MVP demo (success metrics in §9 are listed but not anchored to a go/no-go decision gate).

### Findings
- **high** Undefined cut order below "polish first" (§2) — "trim via the epics' scope-guard cut order" defers the actual ranked sequence to epics-and-stories.md; if that file is not read before a scope crisis, the decision-maker has no triage guidance. *Fix:* inline a numbered cut sequence (e.g., FR-7.7 gut-check prompts → FR-7.8 context handoff → FR-9.1 auto-detect → FR-7.9 chat persistence → …) directly in §2.
- **medium** No go/no-go gate on success metrics (§9) — seven acceptance items are listed but none is marked mandatory-for-ship vs. conditional. A demo that fails item 6 ("test user reports feeling more confident") has no specified consequence. *Fix:* mark each metric as BLOCKING or ADVISORY.
- **low** Open items (§12) lack owners and due-dates — R1, R2, X1, O2 are flagged but carry no assignee or "resolve by Day-1" marker. *Fix:* add "Owner:" and "Resolve by:" to each open item row.

---

## 2. Substance over theater — adequate

Most content is earned. The Priya persona in §3 is grounded ("salaried, Tier-1/2 India, EMI-carrying, emotionally overwhelmed, avoids her banking app") rather than generic. NFR-1's constraint ("no displayed number may cause a missed committed obligation") is concrete. NFR-4 specifies exact model names, a cost ceiling, and batch/caching strategies — that is not boilerplate.

Two phrases are theater that could migrate into any consumer-finance PRD unchanged: (a) §1 "turn financial confusion into financial confidence" and (b) capability 9 "leave the application feeling more informed and confident than when they opened it." Both survive because they are operationalized elsewhere (Priya's attributes in §3, JTBD proxy in §9 item 6) — but the operationalization is in different sections and a reader skimming §1–2 sees only the generic shell. The "honesty spine" framing is used nine times across the document; it is doing real load-bearing work (the deterministic/LLM separation is the product thesis), so its repetition is appropriate.

NFR-2 ("runs on a local dev machine") has no performance threshold — no target for parse time, page-load time, or Copilot response latency on the local machine. For a 3-day demo build, that may be acceptable, but it means a 45-second parse is technically compliant.

### Findings
- **medium** NFR-2/NFR-5 have no latency or performance thresholds — the entire NFR section is constraint-framed (what the system must not do) but silent on what acceptable local performance looks like. *Fix:* add soft targets: parse time < 30 s for a 200-row CSV; Dashboard load < 2 s; Copilot first-token < 3 s. Even as informal targets they scope the build.
- **low** §1 "turn financial confusion into financial confidence" and §2 capability 9 ("leave the application feeling more informed") are generic vision copy — they could appear verbatim in Mint, YNAB, or any finance product. They are partially operationalized in §9 but the §1/§2 copy itself adds no product-specific signal. *Fix:* sharpen §1 to lead with the differentiator: "show Priya a single, honestly-sourced Safe-to-Spend number she can trust — traceable from her own statement."

---

## 3. Strategic coherence — adequate

The product thesis is clear and consistently enforced: honest, traceable numbers build trust; the LLM narrates but never computes. This thesis runs through FR-4 (deterministic engine), FR-5 (score_events log), FR-7.2 (read-only tools), FR-8.2 (exact data points, never approximated), and NFR-1/NFR-3. The feature arc (upload → categorize → compute → narrate → ask) is coherent and every FR maps to a step in it.

Success metrics in §9 validate the thesis partially: items 4 (traceability), 5 (no invented numbers), and 7 (honesty layer spot-check) directly test the core claim. Item 3 (≥90% auto-categorized) is an operational quality gate. Item 6 ("test user reports feeling more informed/confident") is the JTBD proxy — appropriate but a single self-report from a single test user is weak validation for a launch-proximate MVP.

Counter-metrics are absent. There is no stated metric for the opposite failure mode: "Priya finds the Safe-to-Spend figure so conservative it is useless" — i.e., false negative confidence rather than false positive. If the buffer + ring-fencing logic is too aggressive, Priya sees ₹200 Safe-to-Spend on a ₹80,000 salary and stops trusting the app. This failure mode is not named anywhere.

### Findings
- **high** No counter-metrics for over-conservatism (§9) — the honesty spine prevents false positives (spending that misses an obligation) but no metric guards against the opposite failure (a Safe-to-Spend figure so conservative it destroys user trust). *Fix:* add a counter-metric: "Safe-to-Spend figure on the demo statement is within 15% of a manual human-computed figure using the same inputs."
- **medium** Single-user self-report as JTBD validation (§9 item 6) — "a test user reports feeling more informed/confident" is one person's impression with no structured instrument. *Fix:* specify a minimal structured prompt (e.g., "on a scale of 1–5, how confident do you feel about your spending right now vs. before?" with ≥4 as the pass threshold) or replace with a behavioral proxy (user completes the golden path without abandoning).

---

## 4. Done-ness clarity — thin

The engine-layer ACs are strong. FR-4 AC references a named pytest scenario file with exact scenario counts (7 core + 3 boundary). FR-3 AC has a specific threshold (≥90%). FR-7 AC has a specific scripted question count (10) and a hard constraint (zero invented numbers). These would pass in a story review.

The UX-layer and tone ACs routinely use language an engineer cannot deterministically verify:

- FR-6 AC: "the briefing reads as a **calm, honest sentence**, not a category dump" — no criterion for passing. Who judges? By what method?
- FR-6 AC: "every number in prose matches the engine output exactly" — correct and verifiable, but no test mechanism is specified.
- FR-8 AC: "**tone is observation, never accusation**" — no test. An LLM could produce accusatory tone on edge inputs; there is no prompt-test or human-review gate.
- FR-5 AC: "score and Safe-to-Spend never tell **contradictory stories**" — "contradictory" has no operational definition. A score of 72 (healthy) paired with a Safe-to-Spend of ₹0 (no uncommitted funds) is factually accurate but feels contradictory; is it a fail?
- FR-4.8: "this divergence is intentional and defensible (briefing = morning snapshot; hero = live); it is **not a bug**" — this is architectural documentation, not an AC. It cannot be tested.
- FR-7.6 AC: "**graceful** honest response on out-of-scope queries" — "graceful" is precisely the kind of vague qualifier the rubric calls out.
- FR-2.6 transport decision is punted: "WebSocket push preferred; 1-second polling as MVP fallback (**must be specified in implementation**)" — this is a build-time decision, not an AC. The AC does not say which transport was chosen.

### Findings
- **critical** FR-6 AC "calm, honest sentence" and FR-8 AC "tone is observation, never accusation" (§FR-6, §FR-8) — neither is testable by an engineer. They depend on human judgment with no rubric. *Fix:* replace with testable proxies: for FR-6, "briefing contains no raw category labels (e.g., 'Food: ₹3,200, Transport: ₹1,100') and does not exceed 80 words"; for FR-8, specify that the LLM prompt includes the SEBI phrasing rule and a unit test asserts the forbidden phrases ("You should…", "We recommend…") are not present in any generated action suggestion.
- **critical** FR-7.6 AC "graceful honest response" (§FR-7) — "graceful" is unverifiable. *Fix:* specify: "Copilot response for out-of-scope queries contains the phrase 'I don't have data on' or an equivalent, does not state a number, and includes one sentence of guidance on what data would help."
- **high** FR-5 AC "score and Safe-to-Spend never tell contradictory stories" (§FR-5) — no operational definition. *Fix:* define the contradiction explicitly: "if Confidence Score ≥ 70, Safe-to-Spend must be > ₹0; if Safe-to-Spend is ₹0, Confidence Score must be < 50 — add this as a named pytest invariant."
- **high** FR-4.8 is architecture documentation masquerading as a requirement (§FR-4) — "this is not a bug" cannot be tested. *Fix:* move to §11 Resolved Decisions (where it belongs) and replace with a genuine AC: "Dashboard hero card and Copilot response both state the current live Safe-to-Spend figure; the briefing timestamp visibly differs from the hero timestamp."
- **medium** FR-2.6 transport decision deferred to implementation (§FR-2) — the AC does not specify which transport was chosen. *Fix:* decide and commit: "WebSocket used for parse progress; if WebSocket handshake fails within 2 s, client falls back to 1-second polling automatically. This is verified by a network-throttle test."

---

## 5. Scope honesty — adequate

Non-goals are explicitly listed in §2 (Account Aggregator, WhatsApp, mobile, cloud, multi-account, scanned PDF, etc.). The MVP data assumption in §3 ("predictable salaried income with an identifiable recurring credit") is explicit and correctly scoped out irregular-income users. §12 open items honestly flags X1 (responsive gap) and O2 (Commitments page ambiguity).

However, several assumptions are implicit rather than tagged:

- FR-2.1: "support ≥2 common Indian-bank CSV shapes" — which banks? This is a silent assumption about which demo statement will be used. If the demo uses HDFC, but only SBI and ICICI shapes are implemented, the demo fails.
- FR-3.1: "common Indian transactions (UPI/NEFT/IMPS counterparties, major merchants)" — the rule coverage baseline is not specified. How many rules? What coverage on the demo statement?
- FR-8.1: "≥3 named patterns from: post-payday spike, death-by-small-purchases, zombie subscriptions, weekend-vs-weekday pace, upcoming-commitment collision" — it is unclear whether all five detectors must be implemented and three must fire, or only three detectors need to exist. The distinction matters for scope.
- No `[ASSUMPTION]` tags anywhere in the document; no `[NON-GOAL]` inline callouts (the out-of-scope section exists but assumptions are prose-embedded).
- `safe-to-spend-scenarios.md` is referenced as a gate artifact (FR-4 AC, §9 item 2) but is not listed in the sources section and its existence cannot be confirmed from this document.

### Findings
- **high** Demo statement is never specified (§FR-2, §FR-3) — "common Indian-bank CSV shapes" and "90% of demo-statement transactions" assume a specific test fixture but never name it. If the demo statement is not agreed before Day-1, the 90% threshold is untestable. *Fix:* name the demo statement (e.g., "HDFC Bank CSV export, July 2026, ~180 transactions") or commit to providing a synthetic fixture and add it to the repository.
- **high** `safe-to-spend-scenarios.md` referenced but not verifiably present (§FR-4 AC, §9 item 2) — the entire engine acceptance gate depends on this file. If it does not exist or diverges from the PRD's FR-4.1/4.2 spec, the AC is hollow. *Fix:* add its path to §Sources, confirm it exists, and add a cross-reference note: "If this file does not exist, the PRD author must create it before implementation begins."
- **medium** FR-8.1 pattern ambiguity — "≥3 named patterns from: [five patterns listed]" does not specify whether all five detectors must be coded or just three. *Fix:* "implement all five detectors; ≥3 must fire on the demo statement" — or explicitly scope out two detectors as Phase 2.
- **low** No `[ASSUMPTION]` or `[NON-GOAL]` inline tags — the format the rubric calls for is absent. Prose is fine for scope-aware readers, but story-creation automation and downstream reviewers benefit from machine-readable tags. *Fix:* tag at minimum: §3 data assumption, §2 single-user assumption, FR-2.1 CSV-shapes assumption.

---

## 6. Downstream usability — thin

FR IDs are present and contiguous within each section (FR-1.1 through FR-1.9, FR-2.1 through FR-2.10, etc.). Priority tags (P0/P1/P2) are consistently applied and the mapping to capabilities (→ *capability N*) is a useful linkage. The API surface table in §8 is clean and actionable.

**Glossary: absent.** This is the most significant downstream usability gap. The following terms are used throughout with no definitions:

- "Prediction Confidence" vs. "Confidence Score" — two distinct concepts (FR-5.1 vs. FR-5.2) with different data types (0–100 integer vs. Low/Med/High enum) and different semantics (financial preparedness vs. data completeness). A developer new to the project will conflate them.
- "honesty spine" — used nine times; never defined.
- "evidence pack" — used in §1 and FR-6.2; never defined.
- "ring-fencing" — used in FR-4.1, FR-4.2, FR-9; never defined.
- "canonical schema" / "canonical transaction schema" — referenced in FR-2.3, FR-2.1; never defined inline (the research doc is the supposed source, but the data model in §7 is a summary, not a schema).
- "score_events" — used in FR-5.3 and §7; no field-level definition.
- "category_source" enum values (rule|llm|user) — listed in FR-3.3 but not in a glossary.
- "direction" field in §7 transactions schema — no definition of the allowed enum values (debit|credit? in|out?).

Cross-references to external documents are numerous: `safe-to-spend-scenarios.md`, `ux-spec-mvp.md`, `A-Product-Brief/project-brief.md`, `B-Trigger-Map/`, `C-UX-Scenarios/`, `prototypes/01-priyas-first-honest-morning-Prototype/HANDOFF.md`, `epics-and-stories.md`, the technical research document. All are referenced by relative path; none has a section anchor. A story author must hunt across all of them to answer basic questions.

### Findings
- **critical** No glossary — "Prediction Confidence" vs. "Confidence Score" are two distinct concepts with different types and semantics used interchangeably by a developer without §5 context. "Evidence pack," "honesty spine," "ring-fencing," "canonical schema," "direction" enum — all undefined. *Fix:* add a §13 Glossary with at minimum: Confidence Score, Prediction Confidence, Safe-to-Spend, ring-fencing, evidence pack, honesty spine, category_source, direction, score_events, canonical transaction schema.
- **high** Seven external documents referenced without section anchors (§Sources, §6, §9, §12) — story creation from this PRD requires reading the full technical research doc, all UX scenario files, and the prototype HANDOFF. No key decision can be found by following a link. *Fix:* for each external reference that carries a buildable decision, inline the decision or add a specific section anchor (e.g., "see `technical-research.md §4.2 Data Schema`").
- **medium** `direction` field in §7 transaction schema has no enum definition — "debit/credit" vs. "in/out" vs. "-1/+1" is a developer decision that should be locked here. *Fix:* add the enum values to the §7 data model row.

---

## 7. Shape fit — thin

The product is explicitly consumer-facing with a named persona ("Priya"), a prototype called "Priya's First Honest Morning," and UX scenarios in a dedicated `C-UX-Scenarios/` directory. For this shape, User Journeys with Priya as a named protagonist — including emotional beats, decision moments, and failure recovery points — are the expected content.

They are absent from this PRD.

The "golden path" in §2 is a screen-sequence list: "Register → (auto) Login → Upload Statement → Transactions Table → Dashboard → AI Insights & Recommendations → AI Copilot." This is capability-spec shaped, not journey-shaped. It has no emotional arc, no decision points ("Priya notices the amber badge and taps it"), no trigger moments (the Trigger Map is referenced but not summarized). Priya is mentioned in §3 (persona definition) and in FR-3.8 and FR-1.5 as a constraint label, but she never appears as a subject of a sentence describing an action.

The UX scenarios ("C-UX-Scenarios/") are acknowledged in the sources section and in the update-pass note, but their content is not embedded or even summarized in this PRD. Open item X1 explicitly flags a gap ("all UX scenarios assume mobile-responsive web; `ux-spec-mvp.md` is silent on responsive") but the gap is between two external documents, not resolvable from within the PRD itself.

For a 3-day build targeting a specific emotional moment ("Priya's First Honest Morning"), the absence of even a single embedded user journey means a developer building the morning briefing screen has no in-document source for what Priya is feeling, what she needs to see first, or what constitutes a successful moment. The brief arc (upload → Priya receives the briefing and feels less overwhelmed) is implicit in the product name but never stated.

### Findings
- **critical** No User Journeys with named protagonist (entire PRD) — Priya is a persona label, not a protagonist. For a consumer product whose prototype is named "Priya's First Honest Morning," the absence of even one embedded journey ("Priya opens the app, sees the morning briefing, taps 'Why ₹3,200?', reads the explanation, and closes the app feeling less overwhelmed") means developers must reconstruct intent from a screen sequence. *Fix:* add a §3.1 User Journey section with 1–2 journeys in the format: trigger → Priya's emotional state → action → what she sees → outcome. These can be one-paragraph narratives; they do not need to be full scenario specs.
- **high** UX scenario content not embedded or summarized (§Sources, §12) — the PRD's tone and honesty constraints (FR-1.5 trust signal, FR-3.8 calm amber, FR-8.3 SEBI phrasing) are traceable to UX scenario decisions that are not visible here. A developer who does not read the UX scenario files will not understand why these constraints exist. *Fix:* inline the "emotional design constraints" from the UX scenarios as a named subsection (e.g., §3.2 Emotional Design Constraints: non-shaming, never accusatory, honest-first, calm tone) — even 5 bullet points would close this gap.
- **medium** Open item X1 (responsive web gap, §12) is flagged but has no resolution path — the PRD acknowledges the UX scenarios assume mobile-responsive but provides no guidance on whether the MVP scope is desktop-only or responsive. *Fix:* resolve before implementation begins: either "MVP is desktop-first, responsive deferred to Phase 2" (explicit non-goal) or "responsive is required — add it as NFR-9."

---

## Mechanical notes

**Glossary drift:** "Prediction Confidence" and "Confidence Score" are the same term in two forms. FR-5.1 defines Confidence Score (0–100, financial preparedness). FR-5.2 defines Prediction Confidence (Low/Med/High, data completeness). Both are used loosely in §9 success metrics without always specifying which is meant. FR-5 AC "confidence chip tooltip fires on tap" — which chip? The Confidence Score chip (FR-5.5) or the Prediction Confidence indicator? The distinction matters for implementation.

**ID gaps:** No gap in FR sub-item numbering. However, FR-9 skips directly from FR-9.4 to AC — there is no FR-9.5 for the Day-31 edge case display behavior, which is a displayable behavior that belongs in an FR, not embedded in FR-9.3. Minor.

**Broken cross-refs:**
- `safe-to-spend-scenarios.md` is referenced three times (FR-4 AC, §9 item 2, FR-4.2 note) with no confirmed path. The file is not in `_bmad-output/planning-artifacts/` based on the sources section.
- `ux-spec-mvp.md` is referenced in §12 open item X1 but has no path and no entry in the sources section.
- `demo-data.json` in §8 is noted as "the reference payload shape" with a path (`prototypes/01-priyas-first-honest-morning-Prototype/`) that is not listed in the sources section and cannot be confirmed from this document.

**Model name drift:** NFR-4 names `claude-opus-4-8` and `claude-sonnet-5`. FR-3.2 names `claude-haiku-4-5`. §6 names `claude-opus-4-8` / `claude-sonnet-5` as a "cost lever." These model names may be internally consistent but should be verified against the Anthropic API's current model ID list before implementation — model IDs in the Anthropic API follow the pattern `claude-[model]-[version]` and the version suffix format (`-4-8`, `-4-5`) is non-standard; confirm these are correct IDs or replace with the canonical forms.

---

## Ranked findings summary (all dimensions)

| Severity | Title | Location |
|---|---|---|
| **critical** | No glossary — Prediction Confidence vs. Confidence Score conflated; eight undefined terms | §6 (absent) |
| **critical** | FR-6 AC "calm, honest sentence" / FR-8 AC "tone is observation, never accusation" — unverifiable by engineer | §FR-6 AC, §FR-8 AC |
| **critical** | FR-7.6 AC "graceful honest response" — "graceful" is unverifiable | §FR-7 AC |
| **critical** | No User Journeys with named protagonist Priya | Entire PRD |
| **high** | Undefined cut order below "polish first" | §2 |
| **high** | Demo statement never specified — 90% AC threshold is untestable | §FR-2, §FR-3, §9 |
| **high** | `safe-to-spend-scenarios.md` referenced as gate artifact but path unconfirmed | §FR-4 AC, §9 |
| **high** | FR-5 AC "score and Safe-to-Spend never tell contradictory stories" — no operational definition | §FR-5 AC |
| **high** | FR-4.8 "not a bug" — architecture doc masquerading as AC | §FR-4 |
| **high** | Seven external docs referenced without section anchors — story creation requires reading all of them | §Sources, §6 |
| **high** | UX scenario content not embedded or summarized | §Sources, §12 |
| **high** | No counter-metrics for over-conservatism failure mode | §9 |
| **medium** | NFR-2/5 have no latency or parse-time thresholds | §5 |
| **medium** | FR-2.6 transport decision deferred to implementation | §FR-2 |
| **medium** | FR-8.1 — ambiguous whether 3-of-5 detectors must be coded or fire | §FR-8 |
| **medium** | `direction` field in §7 schema has no enum definition | §7 |
| **medium** | Single-user self-report as JTBD validation | §9 item 6 |
| **medium** | Open item X1 (responsive gap) has no resolution path | §12 |
| **low** | §1 vision copy ("turn financial confusion into financial confidence") is generic | §1 |
| **low** | Open items §12 lack owners and due-dates | §12 |
| **low** | No `[ASSUMPTION]` / `[NON-GOAL]` inline tags | §2, §3 |
| **low** | Model name version suffix format should be verified against API canonical IDs | §FR-3.2, §NFR-4 |
