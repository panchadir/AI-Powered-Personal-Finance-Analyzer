"""Statement ingestion: StatementParser protocol, CSV/PDF parsers, normalizer, dedup.

Public API is exposed here; internal helpers are prefixed ``_``. Parsers normalize
to the canonical ``Transaction`` schema before returning (AD-6). Populated in Epic 2.
"""
