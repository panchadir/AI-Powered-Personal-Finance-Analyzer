# PRD Quality Review — AI-Powered Personal Finance Analyzer MVP

**PRD:** `_bmad-output/planning-artifacts/prd.md`
**Run at:** 2026-07-08
**Reviewer:** bmad-prd validate subagent (rubric-walker)

---

## Overall verdict

The PRD's technical core is genuinely strong — the deterministic engine spec, read-only Copilot architecture, and engine ACs are specific enough to gate a real build. However, for a consumer product whose thesis is an emotional shift in a named protagonist, three ACs rely on unjudged human impressions ("tone contract reviewable via demo run," "graceful," "SEBI phrasing verified"), and the user journey section is capability-list-shaped rather than protagonist-shaped. **Grade: Good** — no broken dimensions; multiple thin findings that benefit from repair before stories are cut.

---

## Decision-readiness — adequate

The scope lock is explicit and honest. The delivery-risk note, kill-signal protocol, and §11 Resolved Decisions (11 items with genuine resolutions) all hold up. The cut order is deferred to the epics document rather than inlined.

### Findings
- **high** DM-1 — Cut order deferred to epics (§2): a decision-maker facing a Day-2 slip cannot triage FR priority without reading a second document. *Fix:* inline the ranked cut sequence directly in §2.
- **medium** DM-2 — No go/no-go gate on §9 success metrics; none marked BLOCKING vs. ADVISORY. *Fix:* mark items 1–6 as BLOCKING, item 7 as ADVISORY.
- **low** DM-3 — §12 open items lack resolve-by dates (R1, R2, O2). *Fix:* add explicit resolve-by conditions to each row.

---

## Substance over theater — adequate

Priya persona is specific and drives real decisions (FR-1.5 trust signal, FR-3.8 amber not red, FR-4.9 honest shortfall). NFR-1 is a hard rule, not boilerplate. NFR-4 names exact model IDs and a $15 cost ceiling. NFR-9 has real thresholds (60s parse, 3s render).

### Findings
- **medium** ST-1 — §1 vision copy ("turn financial confusion into financial confidence") is generic and could swap into any consumer finance product. The differentiator (traceable numbers, honesty spine) isn't in the first sentence. *Fix:* lead with the structural differentiator.
- **low** ST-2 — NFR-9 has no Copilot first-token latency target. *Fix:* add "Copilot first-token-to-UI < 3s on a local Claude API call."

---

## Strategic coherence — adequate

Product thesis ("the real competitor is avoidance / honesty is the structural moat") runs consistently through FR-4, FR-5, FR-7.2, FR-8.2, NFR-3. Feature prioritization follows the thesis — engine + honesty spine is "never cut." Counter-metric exists and is correctly placed.

### Findings
- **high** SC-1 — §9 item 7 ("test user reports feeling more informed/confident") is an unstructured single self-report with no pass threshold. For a product whose entire thesis is "this feels better than looking away," this is the most important metric with the weakest specification. *Fix:* add a 1–5 scale with a pass threshold, or replace with a behavioral proxy (completes golden path without abandoning).
- **medium** SC-2 — Over-conservatism counter-metric is binary (never ₹0) but doesn't catch the case where STS shows ₹200 on an ₹80k salary due to over-eager ring-fencing. *Fix:* add a second counter-metric: "STS on Scenario 1 inputs is within 15% of the manually-computed expected value."

---

## Done-ness clarity — thin

Engine-layer ACs (FR-4, FR-3, FR-7) are specific, fixture-referenced, and field-asserting. UX/tone ACs are systematically unverifiable by an engineer.

### Findings
- **critical** DC-1 — FR-6 AC "briefing passes the tone contract (reviewable via the demo run)" is not a testable AC. "Reviewable via demo run" = a human watches and judges with no stated pass criterion. FR-8 AC "SEBI phrasing rule verified in generated text" has the same problem — "verified" by whom, how, when? *Fix FR-6:* replace with: "briefing does not exceed 80 words; every number in prose matches engine output (unit-testable with known fixture); no raw category label appears." *Fix FR-8:* replace with: "no generated Action text contains 'You should,' 'We recommend,' or 'You must' — assert this as a unit test on the insight generator."
- **critical** DC-2 — FR-7.6 AC "graceful honest response" — "graceful" is not testable. The FR body already has specific copy ("I don't have enough data for that"). *Fix:* AC should quote: "response contains a phrase matching 'don't have' or 'don't know,' does not state a number, and is verified against 3 scripted out-of-scope queries in `demo-data.json`'s `copilot_samples`."
- **high** DC-3 — FR-5 AC "Score and Safe-to-Spend never contradict" lacks an operational invariant. The parenthetical example is partial, not a complete rule. *Fix:* "if safe_to_spend_today == 0 then confidence_label != 'Well prepared'; if confidence_label == 'Well prepared' then safe_to_spend_today > 0 — assert as a pytest invariant."
- **high** DC-4 — FR-4.11 "This is intentional, not a bug" is architecture documentation embedded in a functional requirement; it has no testable consequence. *Fix:* remove or replace with a real AC: "dashboard hero timestamp and briefing timestamp visually differ after hero recalculation; both are displayed."
- **medium** DC-5 — FR-2.6 WebSocket assumption carries an AC without a fallback AC. *Fix:* add: "if WebSocket handshake fails within 2s, client falls back to 1-second polling and parse steps still report in sequence."

---

## Scope honesty — adequate

Non-goals are real and specific. §3 MVP data assumption (salaried income, irregular-income users out of scope) is explicit. §11 has genuine resolutions.

### Findings
- **high** SH-1 — `demo-data.json` is referenced in three ACs (FR-2, FR-7, FR-8) but its path (`data/demo-data.json`) is unconfirmed as existing at build start. *Fix:* add to §Sources with full path; add Day-0 action item.
- **medium** SH-2 — FR-2.1 "≥2 common Indian-bank CSV shapes" — which banks? The second bank shape is unspecified. *Fix:* name both banks explicitly and add `[ASSUMPTION]` tag.
- **low** SH-3 — FR-8.1 — status of the 2 non-firing detectors is ambiguous (coded-but-dormant vs. not-production-quality). *Fix:* "all five detectors are production-quality and unit-tested; only ≥3 need fire on the demo dataset."

---

## Downstream usability — adequate

FR IDs are contiguous, priority tags consistent, API surface table actionable, Glossary (§13) substantive with 13 defined terms properly distinguishing Confidence Score from Prediction Confidence.

### Findings
- **high** DU-1 — Seven source documents referenced without section anchors. A story author building FR-4.2 must find the Reservation Rule in `problem-solution-2026-07-07.md` unaided. *Fix:* add section anchors to each load-bearing external reference (partially applied: §Sources now includes "§3 Design Decisions DD-1/DD-2").
- **medium** DU-2 — `ux-spec-mvp.md` was absent from §Sources (load-bearing companion). **FIXED this session.**
- **medium** DU-3 — `score_events` field-level types undefined in §7. *Fix:* add "trigger_event: string enum of known event types" to the Glossary entry or §7 table.

---

## Shape fit — thin

This is a consumer-facing, chain-top PRD that feeds UX → architecture → stories. The §3 journey exists but reads as an annotated capability walkthrough, not a protagonist-centered narrative. The finalized disk version has already fixed this — the reviewed draft should match it.

### Findings
- **critical** SF-1 — §3 User Journey is capability-list-shaped; Priya appears as a feature label, not an emotional protagonist. The disk version (with emotional beats: "She is anxious… She feels calmer") is the correct version. *Fix:* ensure the live file matches the disk version's protagonist narrative.
- **high** SF-2 — Emotional design constraints are distributed across FRs but never summarized in one place. *Fix:* add a §3.1 Emotional Design Constraints subsection (5 bullets): (1) Never blame/shame; (2) Trust signals before data entry; (3) Confidence caveats paired with positive framing; (4) Every number explainable; (5) Uncertainty named, not hidden.

---

## Mechanical notes

- **Glossary drift:** None. "Confidence Score" vs. "Prediction Confidence" used consistently throughout.
- **ID continuity:** Clean — no gaps or duplicates across FR-1.1 through FR-9.4.
- **Broken cross-references (pre-fix):** (1) `demo-data.json` path unconfirmed; (2) `ux-spec-mvp.md` absent from §Sources — **fixed**; (3) `HANDOFF.md` uses `../../prototypes/` relative path — resolves outside `_bmad-output/`.
- **Assumptions Index:** One `[ASSUMPTION]` tag inline (FR-2.6). Several prose-embedded assumptions lack tags: FR-2.1 CSV bank shapes, §3 single-salary income assumption, `demo-data.json` existence.
- **Model IDs:** `claude-haiku-4-5`, `claude-opus-4-8`, `claude-sonnet-5` — verify against current Anthropic canonical IDs via the `claude-api` skill before Day-1 build.

---

## Finding counts by severity
- Critical: 3 (DC-1, DC-2, SF-1)
- High: 7 (DM-1, DC-3, DC-4, SH-1, DU-1, SC-1, SF-2)
- Medium: 7 (DM-2, ST-1, SC-2, DC-5, SH-2, DU-2, DU-3)
- Low: 5 (DM-3, ST-2, SH-3, Mech×2)
