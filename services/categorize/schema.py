"""Single source of truth for the category enum (AD-7).

The Tier-2 LLM categorization call constrains its ``category`` field to a ``Literal``
enum defined here, imported by all callers so free-text categories are structurally
impossible. Populated in Epic 3 (Story 3.2). Intentionally empty in Story 1.1.
"""
