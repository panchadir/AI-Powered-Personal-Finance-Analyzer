"""Framework-agnostic business logic.

No module here may depend on the Reflex framework or its namespace alias
(AD-2, AD-14) — see tests/test_service_boundary.py. ``pytest services/`` must run
without starting a Reflex app. This boundary is what makes the Phase 2 FastAPI
extraction a re-skin, not a rewrite.
"""
