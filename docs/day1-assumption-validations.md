# Day-1 Assumption Validations (Story 1.1)

Records the outcome of the flagged Day-1 validations required before the build proceeds.
See `ARCHITECTURE-SPINE.md` (Stack table, line 204) and `epics.md` Story 1.1 AC #4.

## statementsparser → HDFC format — ✅ PASS (with caveats)

**Validated:** 2026-07-09 · `statementsparser==0.1.0`

**Result:** The library **ships and registers a dedicated HDFC parser.**
`statementparser.parsers.registry.list_parsers()` returns `['AXIS', 'HDFC', 'ICICI', 'SBI']`,
and `statementparser.parsers.hdfc.HDFCParser` is a concrete class. Amounts are modelled
with `Decimal` (consistent with AD-8). Locked in as a repeatable guard:
`tests/ingestion/test_statementsparser_smoke.py`.

**Caveats carried forward to Epic 2:**

1. **Import-name gotcha.** The PyPI distribution is `statementsparser` (with an "s"),
   but the Python import name is `statementparser` (no "s"). Use
   `import statementparser` in `services/ingestion/`.
2. **Schema adaptation required (AD-6).** The library's `Transaction` shape
   (`date, value_date, narration, description, amount, withdrawal, deposit,
   closing_balance, type, payment_method, category, upi, balance_verified`) is **not**
   our canonical schema (`date, description_raw, merchant_normalized, amount,
   direction, balance_after, …`). Story 2.1's `StatementParser` adapter must map
   between them — do not let the vendor shape leak past `services/ingestion/`.
3. **Live-parse confirmation still owed.** This validation confirms HDFC *support*
   exists; it does **not** yet parse the actual Priya demo HDFC PDF (the demo fixture
   and `data/demo-data.json` do not exist yet). The golden-file live-parse test is
   Epic 2 **Story 2.3** — that is where "parses to exactly 24 rows" is proven.

**Top-level API for reference:**
`statementparser.parse(file_path: str, *, password=None, bank=None, categorize=True, verify_balance=True) -> Statement`

## Reflex go/no-go (Day 2 noon) — pending

Not part of Story 1.1. The `services/` framework-agnostic boundary (AD-2/AD-14,
guarded by `tests/test_service_boundary.py`) is in place, which keeps the Streamlit
escape-hatch swap cheap if `rx.State` reactivity blocks at the Day-2 checkpoint.
