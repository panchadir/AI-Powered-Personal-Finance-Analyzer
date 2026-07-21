"""rx.State subclasses, one per page domain (e.g. upload_state, dashboard_state).

State handlers are the ONLY callers of ``services/`` functions from the UI layer
(AD-2) and the ONLY path that mutates financial state, via ``services/engine/`` (AD-3).
Populated per epic.
"""
