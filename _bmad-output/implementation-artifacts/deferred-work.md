# Deferred Work Ledger

Items surfaced during reviews that are real but intentionally not actioned now.

## Deferred from: code review of story-1.1 (2026-07-09)

- ~~**AD-2 boundary guard is reflex-only.** `tests/test_service_boundary.py` detects `import reflex` / `from reflex import` but not a `services/` module importing the UI layer (`from finance_app import …`), which also violates the one-way UI→Service→Data dependency direction (AD-2).~~ **✅ RESOLVED 2026-07-09** (same session, at user request): guard generalized to check top-level import roots; new `test_no_ui_layer_import_in_services` flags any `services/`→`finance_app` import. Detection verified; suite 6 passed. No longer deferred.
