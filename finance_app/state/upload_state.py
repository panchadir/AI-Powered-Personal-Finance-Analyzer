"""Statement-upload state (Story 2.4 UI), mirroring WDS prototype ``01.3-statement-upload.html``.

Validates the chosen file (extension / MIME / size / empty / content sniff), then runs the
transparent parse card (Reading -> Identifying -> Rules -> AI assist) and shows the
"N by rules · M by AI · K need your help" summary before enabling the Dashboard CTA.

Story 2.4 wires the **real** parser: ``services.ingestion.parse_statement`` turns the uploaded
bytes into canonical transactions. Story 3.1 wires the real Tier-1 rules engine (step 3).
Story 3.2 wires the real Tier-2 LLM categorizer (step 4) — both tiers now run **before** the
single persist call, so the DB is only ever written once per upload with the fully-categorized
result (no persist-then-update two-pass). If Tier-2 fails (network/auth/rate-limit — a real,
reachable failure mode for an external API call), the upload does not fail: the Tier-1-only
result is used and those rows simply stay ``UNCATEGORIZED`` (AD-12 honest degradation, same
instinct as Story 3.1's malformed-row skip).

Progress is pushed to the browser over Reflex's existing WebSocket via ``yield`` (no polling
needed — Reflex state sync is already a server push; the 1-second-polling fallback in the AC is
only relevant if that socket is unavailable, which Reflex itself manages).
"""
from __future__ import annotations

import asyncio
import logging

import reflex as rx
import sqlmodel
from pydantic import BaseModel
from anthropic import Anthropic
from sqlmodel import select

from finance_app.models import MerchantRule, Transaction as TxnModel, UploadedFile
from finance_app.state.auth_state import (  # noqa: F401
    AuthState,
    HOME_ROUTE,
    LOGIN_ROUTE,
    user_for_token,
)
from services.categorize import categorize_rules
from services.categorize.llm_categorizer import ClaudeCategorizer
from services.categorize.protocol import Categorizer
from services.categorize.summary import summarize_categorization
from services.categorize.teach_me import load_user_merchant_rules
from services.ingestion import IngestionError, parse_statement, persist_transactions

log = logging.getLogger(__name__)

# Composition root (project-context Dependency Injection rule): the Anthropic client is
# constructed once here, not inside services/categorize/. Construction never fails even
# without ANTHROPIC_API_KEY set (the SDK only raises on an actual request) — a missing key
# surfaces as the Tier-2-failure fallback below, not an app-startup crash.
_categorizer: Categorizer = ClaudeCategorizer(Anthropic())

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
# map 1:1. All four are real as of Story 3.2 (Tier-1 since 3.1, Tier-2 since 3.2).
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


class FileRow(BaseModel):
    """Display-only snapshot of an uploaded file for the statements grid."""

    id: int
    filename: str
    status: str
    uploaded_at: str  # pre-formatted "DD Mon YYYY, HH:MM" for display


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
    has_prior_uploads: bool = False  # True when the user already has statements in the DB

    # Parse results — all real as of Story 3.2 (Tier-1 + Tier-2 both run before persist).
    total: int = 0
    rules: int = 0
    ai: int = 0
    need_review: int = 0
    # Story 8.1 (AC4): set True when the Tier-2 LLM categorizer fails so the upload
    # page can show an honest dismissable caveat banner.
    ai_caveat: bool = False

    @rx.var
    def dashboard_enabled(self) -> bool:
        """Dashboard button is active if a fresh parse just finished OR prior uploads exist."""
        return self.summary_visible or self.has_prior_uploads

    # Uploaded statements grid
    uploaded_files: list[FileRow] = []
    delete_error: str = ""

    @rx.event
    def reset_page(self):
        self.error = self.filename = self.active_step = ""
        self.parsing = self.summary_visible = self.ai_caveat = False
        self.done_steps = []
        self.total = self.rules = self.ai = self.need_review = 0
        with rx.session() as session:
            user = user_for_token(session, self.auth_token)
            if user is not None:
                self.has_prior_uploads = session.exec(
                    select(UploadedFile).where(UploadedFile.user_id == user.id).limit(1)
                ).first() is not None
        self.delete_error = ""

    @rx.event
    def dismiss_ai_caveat(self):
        """Dismiss the Tier-2 failure caveat banner (Story 8.1 AC4)."""
        self.ai_caveat = False

    @rx.event
    def load_uploaded_files(self):
        """Load the user's uploaded statements for the grid."""
        with rx.session() as session:
            user = user_for_token(session, self.auth_token)
            if user is None:
                self.uploaded_files = []
                return
            rows = session.exec(
                sqlmodel.select(UploadedFile)
                .where(UploadedFile.user_id == user.id)
                .order_by(UploadedFile.uploaded_at.desc())
            ).all()
            self.uploaded_files = [
                FileRow(
                    id=r.id,
                    filename=r.filename,
                    status=r.status,
                    uploaded_at=r.uploaded_at.strftime("%d %b %Y, %H:%M"),
                )
                for r in rows
            ]

    @rx.event
    def delete_file(self, file_id: int):
        """Delete an uploaded file and its transactions."""
        self.delete_error = ""
        try:
            with rx.session() as session:
                user = user_for_token(session, self.auth_token)
                if user is None:
                    return
                file_row = session.exec(
                    sqlmodel.select(UploadedFile).where(
                        UploadedFile.id == file_id,
                        UploadedFile.user_id == user.id,
                    )
                ).first()
                if file_row is None:
                    return
                # Delete linked transactions first (no cascade defined in model)
                session.exec(
                    sqlmodel.delete(TxnModel).where(TxnModel.source_file_id == file_id)
                )
                session.delete(file_row)
                session.commit()
        except Exception:
            log.exception("Failed to delete uploaded file id=%d", file_id)
            self.delete_error = "Could not delete the statement. Please try again."
            return
        # Refresh the list after deletion
        self.load_uploaded_files()

    @rx.event
    def logout(self):
        self.do_logout()
        return rx.redirect(LOGIN_ROUTE)

    @rx.event
    def go_review(self):
        """The Dashboard CTA. Enabled once the user has data — either a fresh parse or prior uploads."""
        if self.summary_visible or self.has_prior_uploads:
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
        self.done_steps = self.done_steps + ["identify"]
        yield

        # Step 3 — Categorising with Tier-1 rules engine (the user's own taught "Teach Me"
        # rules, Story 3.3, are checked before the built-in table). Loading rules is a cheap
        # DB read — no to_thread needed, unlike the categorization call itself.
        self.active_step = "rules"
        yield
        user_rules: list[tuple[str, str]] = []
        with rx.session() as session:
            user = user_for_token(session, self.auth_token)
            if user is not None:
                user_rules = load_user_merchant_rules(session, MerchantRule, user.id)
        categorized = await asyncio.to_thread(categorize_rules, transactions, user_rules)
        self.active_step = ""
        self.done_steps = self.done_steps + ["rules"]
        yield

        # Step 4 — AI assist: Tier-2 LLM categorizer on whatever Tier-1 left UNCATEGORIZED.
        # ClaudeCategorizer.categorize() already catches its own failures (network/auth/
        # rate-limit/malformed-response) and returns the input unchanged — this try/except
        # is a defense-in-depth backstop, not the primary fallback mechanism.
        self.active_step = "ai"
        yield
        try:
            categorized = await asyncio.to_thread(_categorizer.categorize, categorized)
        except Exception:  # noqa: BLE001
            log.exception("Tier-2 categorization failed for %r; continuing with Tier-1 only", name)
            self.ai_caveat = True  # Story 8.1 AC4: surface dismissable caveat banner
        self.active_step = ""
        self.done_steps = self.done_steps + ["ai"]
        yield

        # Persist the fully-categorized (Tier-1 + Tier-2) rows in a single write.
        _session_expired = False
        try:
            with rx.session() as session:
                user = user_for_token(session, self.auth_token)
                if user is None:
                    # Session expired during the long parse/categorise cycle. Treat as
                    # auth failure — never show a false-success summary for unsaved data.
                    log.warning("Session expired before persisting %r — redirecting to login", name)
                    self.parsing = False
                    self.active_step = ""
                    _session_expired = True
                elif not categorized:
                    # Parsed to an empty list (e.g. Tier-2 failure returned nothing and
                    # Tier-1 also found nothing) — nothing to persist, show honest summary.
                    pass
                else:
                    uploaded = UploadedFile(  # type: ignore[call-arg]
                        user_id=user.id, filename=name, status="parsed"
                    )
                    session.add(uploaded)
                    session.commit()
                    session.refresh(uploaded)
                    persist_transactions(session, TxnModel, user.id, uploaded.id, categorized)
        except Exception:  # noqa: BLE001
            log.exception("Failed to persist parsed statement %r", name)
            self.parsing = False
            self.active_step = ""
            self.error = "We read your statement but couldn't save it. Please try again."
            yield rx.call_script(_CLEAR_LEAVE_GUARD)
            yield
            return

        # Redirect happens after the session is closed — no connection held across yields.
        if _session_expired:
            yield rx.call_script(_CLEAR_LEAVE_GUARD)
            yield rx.redirect(LOGIN_ROUTE)
            return

        # Real, honest three-way summary — see summarize_categorization()'s docstring for
        # why a real category (e.g. the rules engine's low-confidence "Transfer In"
        # fallback) can still count toward need_review, not rules.
        summary = summarize_categorization(categorized)
        self.rules = summary.rules
        self.ai = summary.ai
        self.need_review = summary.need_review
        self.parsing = False  # always clear before showing summary (Finding 2 fix)
        self.summary_visible = True
        self.load_uploaded_files()
        yield rx.call_script(_CLEAR_LEAVE_GUARD)
        yield rx.redirect("/dashboard")