# Logical View Map — Scenario 01: Priya's First Honest Morning

**Created:** 2026-07-08
**Method:** WDS Phase 5 — Prototyping, Step 2 (Scenario Analysis)

A "logical view" is a conceptual page/screen with multiple states. Scenario 01 is a **linear golden path**: 7 scenario steps map 1:1 to 7 distinct logical views (no view reuse within the scenario).

---

## Views

| # | Logical View | Step(s) | Type | Auth | Spec |
|---|-------------|---------|------|------|------|
| V1 | Register | 01.1 | Form page | Public | `.../01.1-register/` |
| V2 | Login (Auto-authentication transition) | 01.2 | Transition screen | Public → Auth | `.../01.2-login/` |
| V3 | Statement Upload | 01.3 | Upload + parse progress | Auth | `.../01.3-statement-upload/` |
| V4 | Transactions Table | 01.4 | List + inline "Teach Me" edit | Auth | `.../01.4-transactions-table/` |
| V5 | Dashboard | 01.5 | Hero Safe-to-Spend briefing | Auth | `.../01.5-dashboard/` |
| V6 | AI Insights & Recommendations | 01.6 | Insight cards | Auth | `.../01.6-ai-insights-recommendations/` |
| V7 | Copilot Chat | 01.7 | Chat interface | Auth | `.../01.7-copilot-chat/` |

---

## View States

| View | States |
|------|--------|
| V1 Register | default · field-validating · validation-error · submitting |
| V2 Login | confirming ("Account created!") · redirecting (progress) · error (token failure, recover) |
| V3 Statement Upload | empty (drop zone) · file-selected · uploading · parsing (transparent progress) · parsed-summary ("X by rules, Y by AI, Z need help") · error |
| V4 Transactions Table | loaded · filtered (category chips) · row-tapped ("Teach Me") · correcting · corrected |
| V5 Dashboard | first-visit loading · default · why-expanded · confidence-tooltip · stale-data warning · low-confidence · error |
| V6 AI Insights | default (insight cards) · evidence-expanded · empty (no insights yet) |
| V7 Copilot Chat | empty (with suggested prompts) · user-typing · streaming answer · answered (with data-trace chips) · error |

---

## Reuse & Cross-Scenario Notes

- **No reuse within Scenario 01** — each of the 7 steps is a structurally distinct page.
- **V7 Copilot Chat** is the shared base for **Scenario 03 (03.1)**, which documents a return-visit gut-check *variant* (quick-prompt bar, Yes/Stretch/No verdict badge, brevity mode). That is a separate scenario — build here as the first-touch exploratory version; the 03 delta comes later.
- The **returning-user manual Login page** (email/password/biometric) referenced in 01.2's note is a separate standalone page, NOT V2. Out of scope for Scenario 01.

---

## Build Order

Linear, matching scenario/navigation order — each page forwards to the next, so building in order lets us click through the whole golden path incrementally:

**V1 → V2 → V3 → V4 → V5 → V6 → V7**

---

## Shared Infrastructure (built alongside V1)

| File | Purpose |
|------|---------|
| `shared/data.js` | Loads `data/demo-data.json`, exposes helpers to all pages |
| `shared/format.js` | ₹ currency formatting, date formatting |
| `shared/nav.js` | Bottom nav (Home/Transactions/Commitments/Copilot) + linear page routing |
| `shared/styles.css` | Gray Model design tokens (grayscale palette, spacing scale, type scale), responsive breakpoints (768/1024/1280) |

---

## Honesty Layer Checklist (applies to every view)

- [ ] Data freshness caveat wherever a number is shown ("Based on your statement from 30 Jun 2026")
- [ ] Confidence never shown as a raw number — only High/Medium/Low chip + tooltip
- [ ] "Why?" reasoning derivable from real demo data (never invented)
- [ ] Copilot answers carry data-trace chips
- [ ] Observation tone, never judgment ("your food spend was ₹7,200" not "you spent too much")
- [ ] "Information not advice" framing (SEBI boundary) — "consider", not "do"
