---
title: "Brief → PRD Reconciliation"
created: 2026-07-08
source_input: A-Product-Brief/project-brief.md
compared_against: planning-artifacts/prd.md
---

# Brief → PRD Reconciliation

**Input document:** `A-Product-Brief/project-brief.md`

## Top 5 Gaps (in brief, missing or weakened in PRD)

### 1. Tone of Voice — full section silently dropped
The brief contains a complete, concrete Tone of Voice section (lines 198–241) with specific copy examples for error messages, button text, empty states, and success messages, plus explicit Do/Don't guidelines. The PRD references "honest, calm, non-judgmental, jargon-free" tone in FR-6.2 only as a parenthetical phrase. The concrete copy contracts (e.g., "Show me why" not "View Details"; "I couldn't reach your bank just now — using your last known balance" not "Error 503") are implementation requirements, not suggestions, and are absent from every FR acceptance criterion.

### 2. Kill-signal protocol — present in brief, absent in PRD
The brief defines an explicit existential kill signal: "a single high-profile Safe-to-Spend error causing real user financial harm triggers an immediate feature pause and trust audit before relaunch." The PRD captures conservative-by-default behavior (NFR-1) but carries no operational protocol for this scenario. This is a non-negotiable safety constraint from the brief, not a risk mitigation.

### 3. Hard regulatory gates — partially carried, key thresholds dropped
The brief states three hard regulatory constraints not fully preserved: (a) FIU registration is legally required to receive AA-consented data — never mentioned in the PRD; (b) a formal legal opinion on the SEBI IA / "information vs. advice" boundary is a hard prerequisite before scaling past ~10,000 users — absent from the PRD's open items or risk register; (c) DPDP Act Rule 4 consent-manager architecture must be built to standard now (November 2026 deadline), not retrofitted — the PRD mentions DPDP compliance only for auth-token storage (FR-1.1) and consent checkboxes (FR-1.7).

### 4. Business model as hypothesis — certainty language crept in
The brief explicitly flags ₹199/₹499 pricing and ≥5% free-to-paid conversion as unvalidated hypotheses and notes India/SEA as the lowest freemium-converting regions globally (1–5%). The PRD cites the business model framing but does not carry forward the hypothesis flag or the global-ceiling risk (~$100M scale cap for pure-subscription PFM). Any roadmap or investor narrative built from the PRD alone will treat these as settled inputs.

### 5. Honesty-as-moat strategic framing — mechanics preserved, competitive logic dropped
The brief articulates a precise competitive argument: incumbents' brand is "always right"; this product's brand is "always honest" (Confidence % + explicit uncertainty); incumbents structurally cannot copy this without undermining their own positioning. The PRD implements the honesty mechanics faithfully (confidence chips, trace chips, "I don't know" responses) but never states the strategic reason — that honesty is the moat, not a UX preference. This framing should appear in at least the Overview section to ensure build decisions preserve it intentionally.

---

*Reconciliation written 2026-07-08. Gaps are additive — the PRD is not contradicted, only incomplete on these points.*
