"""Statement-upload state (Story 2.4 UI), mirroring WDS prototype ``01.3-statement-upload.html``.

Validates the chosen file (extension / MIME / size / empty / content sniff), then runs the
transparent parse card (Reading -> Identifying -> Rules -> AI assist) and shows the
"N by rules · M by AI · K need your help" summary before enabling the Dashboard CTA.

Story 2.4 wires the **real** parser: ``services.ingestion.parse_statement`` turns the uploaded
bytes into canonical transactions, so the transaction *total* is real. Categorization (the
"by rules" / "by AI" split) is Epic 3 (S3.1/S3.2) — until then steps 3 and 4 fire as skeleton
events and every parsed row counts as "needs your help". Persisting the parsed rows (with dedup
and ``user_id``/``source_file``) is Story 2.5; 2.4 parses and reports the honest count.

Progress is pushed to the browser over Reflex's existing WebSocket via ``yield`` (no polling
needed — Reflex state sync is already a server push; the 1-second-polling fallback in the AC is
only relevant if that socket is unavailable, which Reflex itself manages).
"""
from __future__ import annotations

import asyncio
import logging

import reflex as rx

from finance_app.models import Transaction as TxnModel, UploadedFile
from finance_app.state.auth_state import (  # noqa: F401
    AuthState,
    HOME_ROUTE,
    LOGIN_ROUTE,
    user_for_token,
)
from services.ingestion import IngestionError, parse_statement, persist_transactions

log = logging.getLogger(__name__)

UPLOAD_ID = "upload-statement"
_MAX_SIZE = 10 * 1024 * 1024  # 10 MB
_ALLOWED_EXT = ("pdf", "csv")
_ALLOWED_MIME = {
    "application/pdf", "text/csv", "application/csv",
    "application/vnd.ms-excel", "text/plain", "",
}

# A small in-repo HDFC-format sample so "Use a sample (demo)" runs a REAL parse (honest counts),
# not a hardcoded fake. Three transactions; two debits + one salary credit.
_SAMPLE_CSV = (
    b"Date,Narration,Chq./Ref.No.,Value Dt,Withdrawal Amt.,Deposit Amt.,Closing Balance\n"
    b"01/06/2026,UPI-SWIGGY-BANGALORE,R1,01/06/2026,450.00,,18000.00\n"
    b"03/06/2026,NEFT-RENT LANDLORD,R2,03/06/2026,15000.00,,3000.00\n"
    b"30/06/2026,SALARY ACME CORP,R3,30/06/2026,,85000.00,88000.00\n"
)

# (key, label) for the four transparent-parse steps shown in order. Labels follow the WDS
# prototype; the AC's step *concepts* (Reading / Identifying / Categorising by Rules / AI Assist)
# map 1:1. Steps "rules"/"ai" are skeleton until Epic 3 fills real categorization counts.
PARSE_STEPS = (
    ("read", "Reading your statement"),
    ("identify", "Identifying transactions"),
    ("rules", "Categorising with our rules"),
    ("ai", "AI assist for ambiguous ones"),
)

# JS toggled around an in-progress parse so a back/close/navigate prompts the browser's native
# "Leave site?" confirmation (FR-2.10). Cleared the moment the parse finishes or fails.
_ARM_LEAVE_GUARD = "window.onbeforeunload = function (e) { e.preventDefault(); e.returnValue = ''; return ''; };"
_CLEAR_LEAVE_GUARD = "window.onbeforeunload = null;"


def _ext_of(name: str) -> str:
    parts = (name or "").lower().rsplit(".", 1)
    return parts[1] if len(parts) > 1 else ""


def validate_statement(name: str, content_type: str, data: bytes) -> str:
    """Return an empty string if the file is an acceptable PDF/CSV, else a friendly error.

    Client-side pre-check (extension -> MIME -> empty -> size -> content sniff) so obvious
    mistakes fail fast; the real parser is the authority and raises typed errors of its own.
    """
    ext = _ext_of(name)
    if ext not in _ALLOWED_EXT:
        return (
            f"Unsupported file type “.{ext or '?'}”. "
            "Please upload a PDF (.pdf) or CSV (.csv) statement."
        )
    if content_type and content_type not in _ALLOWED_MIME:
        return (
            f"This file doesn't look like a genuine {ext.upper()} (its type is "
            f"“{content_type}”). Please upload a real PDF or CSV."
        )
    if len(data) == 0:
        return "That file is empty. Please upload a statement that contains transactions."
    if len(data) > _MAX_SIZE:
        return "That file is too large (max 10 MB). Try exporting a single month."
    head = data[:1024]
    if ext == "pdf":
        if data[:5] != b"%PDF-":
            return "This PDF appears to be corrupted or isn't a real PDF. Try re-downloading your statement."
    else:  # csv
        if b"\x00" in head:
            return "This CSV appears to be corrupted or isn't plain text. Please export a fresh CSV from your bank."
        if b"," not in head and b"\n" not in head:
            return "We couldn't find any columns in this CSV. Please upload a bank statement export."
    return ""


class UploadState(AuthState):
    """Drives the upload zone, validation errors, and the real parse -> summary flow."""

    error: str = ""
    filename: str = ""
    parsing: bool = False  # swaps the drop zone for the progress card
    active_step: str = ""  # the step currently spinning
    done_steps: list[str] = []  # completed steps (checked)
    summary_visible: bool = False  # parse summary + enabled CTA

    # Parse results. `total` is real (from the parser); the rules/ai split is skeleton until
    # Epic 3, where every row is currently "needs review".
    total: int = 0
    rules: int = 0
    ai: int = 0
    need_review: int = 0

    @rx.event
    def reset_page(self):
        self.error = self.filename = self.active_step = ""
        self.parsing = self.summary_visible = False
        self.done_steps = []
        self.total = self.rules = self.ai = self.need_review = 0

    @rx.event
    def logout(self):
        self.do_logout()
        return rx.redirect(LOGIN_ROUTE)

    @rx.event
    def go_review(self):
        """The Dashboard CTA. Guarded so an aria-disabled (focusable) button can't act early."""
        if self.summary_visible:
            return rx.redirect("/dashboard")

    @rx.event
    async def handle_upload(self, files: list[rx.UploadFile]):
        """Validate the dropped/chosen file, then parse it for real."""
        self.error = ""
        if not files:
            self.error = "No file selected. Please choose a statement to upload."
            return
        f = files[0]
        name = f.name or getattr(f, "filename", "") or "statement"
        data = await f.read()
        err = validate_statement(name, f.content_type or "", data)
        if err:
            self.error = err
            return
        async for event in self._run_parse(name, data):
            yield event

    @rx.event
    async def use_sample(self):
        """'Use a sample statement (demo)' — parses a bundled sample CSV for real."""
        self.error = ""
        async for event in self._run_parse("sample-statement.csv", _SAMPLE_CSV):
            yield event

    async def _run_parse(self, name: str, data: bytes):
        """Animate the four steps around a real parse; reveal the honest summary + CTA.

        The real parse (``parse_statement``) runs in a worker thread so the event loop keeps
        pushing progress. A typed ``IngestionError`` is translated to plain-language copy and
        never re-raised to the UI (AD-12).
        """
        self.reset_page()
        self.filename = name
        self.parsing = True
        yield rx.call_script(_ARM_LEAVE_GUARD)  # FR-2.10: warn on back/close mid-parse
        yield

        # Step 1 — Reading.
        self.active_step = "read"
        yield
        await asyncio.sleep(0.3)
        self.done_steps = self.done_steps + ["read"]

        # Step 2 — Identifying: the real parse happens here.
        self.active_step = "identify"
        yield
        try:
            transactions = await asyncio.to_thread(parse_statement, name, data)
        except IngestionError as exc:
            # Honest refusal: plain-language copy, drop back to the upload view.
            self.parsing = False
            self.active_step = ""
            self.error = exc.message
            yield rx.call_script(_CLEAR_LEAVE_GUARD)
            yield
            return
        self.total = len(transactions)
        # Story 2.5: persist the parsed rows — deduped on the canonical key and scoped to the
        # signed-in user (AD-4) — so Review/Dashboard read real data. A re-upload or overlapping
        # range inserts only genuinely-new rows. `source_file_id` ties rows to this upload.
        try:
            with rx.session() as session:
                user = user_for_token(session, self.auth_token)
                if user is not None and transactions:
                    uploaded = UploadedFile(  # type: ignore[call-arg]
                        user_id=user.id, filename=name, status="parsed"
                    )
                    session.add(uploaded)
                    session.commit()
                    session.refresh(uploaded)
                    persist_transactions(session, TxnModel, user.id, uploaded.id, transactions)
        except Exception:  # noqa: BLE001
            # Never show a success summary for data we failed to save (AD-12). Log with
            # context, surface honest copy, clear the leave-guard, and drop back to Upload.
            log.exception("Failed to persist parsed statement %r", name)
            self.parsing = False
            self.active_step = ""
            self.error = "We read your statement but couldn't save it. Please try again."
            yield rx.call_script(_CLEAR_LEAVE_GUARD)
            yield
            return
        self.active_step = ""
        self.done_steps = self.done_steps + ["identify"]
        yield

        # Steps 3 & 4 — Categorising by rules / AI assist: skeleton until Epic 3 (S3.1/S3.2).
        for key in ("rules", "ai"):
            self.active_step = key
            yield
            await asyncio.sleep(0.3)
            self.active_step = ""
            self.done_steps = self.done_steps + [key]
            yield

        # Honest summary: real total; categorization not run yet, so all rows need review.
        # Epic 3 replaces rules/ai with real Tier-1/Tier-2 counts.
        self.rules = 0
        self.ai = 0
        self.need_review = self.total
        self.summary_visible = True
        yield rx.call_script(_CLEAR_LEAVE_GUARD)
        yield