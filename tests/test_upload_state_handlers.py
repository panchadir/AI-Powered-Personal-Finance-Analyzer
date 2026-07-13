"""Coverage for ``finance_app/state/upload_state.py`` — the pure validator plus the async
parse pipeline (``handle_upload`` / ``use_sample`` / ``_run_parse``).

The real ``parse_statement`` / Tier-1 rules run for the happy ``use_sample`` path (deterministic,
LLM-free); the failure branches monkeypatch ``parse_statement`` and the module's ``_categorizer``
so every arm of ``_run_parse`` (ingestion error, session-expired, persist failure, Tier-2 caveat)
is exercised. Handlers are driven through the ``make_state`` harness (see ``tests/conftest.py``).
"""
from __future__ import annotations

import pytest

import finance_app.state.upload_state as upload_mod
from finance_app.models import Transaction, UploadedFile
from finance_app.state.upload_state import UploadState, validate_statement
from services.ingestion import IngestionError
from tests.conftest import drive


# ---------------------------------------------------------------------------
# validate_statement — pure, every branch
# ---------------------------------------------------------------------------

class TestValidateStatement:
    def test_accepts_a_real_pdf(self):
        assert validate_statement("stmt.pdf", "application/pdf", b"%PDF-1.7 body") == ""

    def test_accepts_a_real_csv(self):
        assert validate_statement("stmt.csv", "text/csv", b"a,b\n1,2\n") == ""

    def test_rejects_unsupported_extension(self):
        assert "Unsupported file type" in validate_statement("stmt.txt", "text/plain", b"x")

    def test_rejects_missing_extension(self):
        assert "Unsupported file type" in validate_statement("statement", "", b"x")

    def test_rejects_mismatched_mime(self):
        assert "doesn't look like a genuine" in validate_statement("stmt.pdf", "image/png", b"%PDF-x")

    def test_rejects_empty_file(self):
        assert "empty" in validate_statement("stmt.pdf", "application/pdf", b"")

    def test_rejects_oversize_file(self):
        big = b"%PDF-" + b"0" * (10 * 1024 * 1024 + 1)
        assert "too large" in validate_statement("stmt.pdf", "application/pdf", big)

    def test_rejects_corrupt_pdf_without_magic_bytes(self):
        assert "corrupted" in validate_statement("stmt.pdf", "application/pdf", b"not a pdf at all")

    def test_rejects_binary_csv(self):
        assert "corrupted" in validate_statement("stmt.csv", "text/csv", b"col\x00umn")

    def test_rejects_csv_with_no_columns(self):
        assert "columns" in validate_statement("stmt.csv", "text/csv", b"noseparatorshere")


# ---------------------------------------------------------------------------
# Simple handlers + computed var
# ---------------------------------------------------------------------------

class TestSimpleHandlers:
    def test_dashboard_enabled_var(self, make_state):
        s = make_state(UploadState)
        assert s.dashboard_enabled is False
        s.summary_visible = True
        assert s.dashboard_enabled is True

    def test_dismiss_ai_caveat(self, make_state):
        s = make_state(UploadState)
        s.ai_caveat = True
        s.dismiss_ai_caveat()
        assert s.ai_caveat is False

    def test_logout_redirects(self, make_state):
        s = make_state(UploadState, auth_token="x")
        assert s.logout() is not None

    def test_go_review_gated_on_data(self, make_state):
        s = make_state(UploadState)
        assert s.go_review() is None  # no data yet
        s.summary_visible = True
        assert s.go_review() is not None

    def test_reset_page_reflects_prior_uploads(self, make_state, seed_auth, db_session):
        uid, token = seed_auth()
        db_session.add(UploadedFile(user_id=uid, filename="old.pdf"))  # type: ignore[call-arg]
        db_session.commit()
        s = make_state(UploadState, auth_token=token)
        s.reset_page()
        assert s.has_prior_uploads is True
        assert s.total == 0 and s.summary_visible is False


# ---------------------------------------------------------------------------
# handle_upload — validation gates before parsing
# ---------------------------------------------------------------------------

class _FakeUpload:
    def __init__(self, name, content_type, data):
        self.name = name
        self.content_type = content_type
        self._data = data

    async def read(self):
        return self._data


class TestHandleUpload:
    def test_no_files_sets_error(self, make_state):
        s = make_state(UploadState, auth_token="x")
        drive(s.handle_upload([]))
        assert "No file selected" in s.error

    def test_invalid_file_sets_error_and_skips_parse(self, make_state):
        s = make_state(UploadState, auth_token="x")
        drive(s.handle_upload([_FakeUpload("bad.txt", "text/plain", b"x")]))
        assert "Unsupported file type" in s.error
        assert s.parsing is False

    def test_valid_file_reaches_parse_and_summary(self, make_state, seed_auth, monkeypatch):
        monkeypatch.setattr(upload_mod, "parse_statement", lambda name, data: [])
        monkeypatch.setattr(upload_mod._categorizer, "categorize", lambda rows: rows)
        _uid, token = seed_auth()
        s = make_state(UploadState, auth_token=token)
        drive(s.handle_upload([_FakeUpload("stmt.csv", "text/csv", b"a,b\n1,2\n")]))
        assert s.error == "" and s.summary_visible is True


# ---------------------------------------------------------------------------
# _run_parse — driven via use_sample (happy path) and monkeypatched failures
# ---------------------------------------------------------------------------

class TestRunParse:
    def test_use_sample_parses_persists_and_summarises(self, make_state, seed_auth, db_session, monkeypatch):
        # Keep the (unusable) Anthropic Tier-2 out of the picture deterministically: it returns
        # its input unchanged, mirroring ClaudeCategorizer's own failure fallback.
        monkeypatch.setattr(upload_mod._categorizer, "categorize", lambda rows: rows)
        uid, token = seed_auth()
        s = make_state(UploadState, auth_token=token)
        drive(s.use_sample())
        assert s.summary_visible is True and s.parsing is False
        assert s.total == 3  # the bundled 3-row sample
        # Rows were persisted for this user.
        from sqlmodel import select
        rows = db_session.exec(select(Transaction).where(Transaction.user_id == uid)).all()
        assert len(rows) == 3

    def test_ingestion_error_surfaces_friendly_copy(self, make_state, seed_auth, monkeypatch):
        def _boom(name, data):
            raise IngestionError("We couldn't read that statement.")

        monkeypatch.setattr(upload_mod, "parse_statement", _boom)
        _uid, token = seed_auth()
        s = make_state(UploadState, auth_token=token)
        drive(s.use_sample())
        assert s.parsing is False and s.summary_visible is False
        assert s.error == "We couldn't read that statement."

    def test_tier2_failure_sets_caveat_but_still_succeeds(self, make_state, seed_auth, monkeypatch):
        monkeypatch.setattr(upload_mod, "parse_statement", lambda name, data: [])

        def _raise(rows):
            raise RuntimeError("rate limited")

        monkeypatch.setattr(upload_mod._categorizer, "categorize", _raise)
        _uid, token = seed_auth()
        s = make_state(UploadState, auth_token=token)
        drive(s.use_sample())
        assert s.ai_caveat is True
        assert s.summary_visible is True  # empty parse still shows an honest summary

    def test_session_expired_before_persist_redirects_to_login(self, make_state, monkeypatch):
        # A parse returns rows, but there is no live session for this token → never a false success.
        monkeypatch.setattr(
            upload_mod, "parse_statement",
            lambda name, data: [],
        )
        monkeypatch.setattr(upload_mod._categorizer, "categorize", lambda rows: rows)
        s = make_state(UploadState, auth_token="no-live-session")
        events = drive(s.use_sample())
        assert s.parsing is False and s.summary_visible is False
        # A redirect event was yielded.
        assert any(e is not None for e in events)

    def test_persist_failure_surfaces_save_error(self, make_state, seed_auth, monkeypatch):
        monkeypatch.setattr(
            upload_mod, "parse_statement",
            lambda name, data: [object()],  # one truthy "row" so we reach persist
        )
        monkeypatch.setattr(upload_mod, "categorize_rules", lambda txns, rules: txns)
        monkeypatch.setattr(upload_mod._categorizer, "categorize", lambda rows: rows)

        def _fail_persist(*a, **k):
            raise RuntimeError("db down")

        monkeypatch.setattr(upload_mod, "persist_transactions", _fail_persist)
        _uid, token = seed_auth()
        s = make_state(UploadState, auth_token=token)
        drive(s.use_sample())
        assert "couldn't save it" in s.error
        assert s.parsing is False
