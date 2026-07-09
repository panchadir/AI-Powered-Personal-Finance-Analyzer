"""Statement-upload state (Story 2.4 UI), mirroring WDS prototype ``01.3-statement-upload.html``.

Validates the chosen file (extension / MIME / size / empty / content sniff), then runs the
prototype's transparent parse animation (Reading → Identifying → Rules → AI assist) and shows
the "N by rules · M by AI · K need your help" summary before enabling the Dashboard CTA.

The **real** statement parser is an Epic 2 concern (``services/ingestion`` is not implemented
yet), so — exactly like the prototype — the transaction counts here come from a demo fallback.
``_PARSE_*`` marks the single integration point where the real parser output will replace them.
"""
from __future__ import annotations

import asyncio

import reflex as rx

from finance_app.state.auth_state import AuthState, HOME_ROUTE, LOGIN_ROUTE  # noqa: F401

UPLOAD_ID = "upload-statement"
_MAX_SIZE = 10 * 1024 * 1024  # 10 MB
_ALLOWED_EXT = ("pdf", "csv")
_ALLOWED_MIME = {
    "application/pdf", "text/csv", "application/csv",
    "application/vnd.ms-excel", "text/plain", "",
}

# Demo fallback counts (prototype parity). Replaced by the real parser in Epic 2 (Story 2.3).
_PARSE_TOTAL = 24
_PARSE_RULES = 18
_PARSE_AI = 3
_PARSE_NEED_REVIEW = 3

# (key, label) for the four transparent-parse steps shown in order.
PARSE_STEPS = (
    ("read", "Reading your statement"),
    ("identify", "Identifying transactions"),
    ("rules", "Categorising with our rules"),
    ("ai", "AI assist for ambiguous ones"),
)


def _ext_of(name: str) -> str:
    parts = (name or "").lower().rsplit(".", 1)
    return parts[1] if len(parts) > 1 else ""


def validate_statement(name: str, content_type: str, data: bytes) -> str:
    """Return an empty string if the file is an acceptable PDF/CSV, else a friendly error.

    Mirrors the prototype's client-side checks (extension → MIME → empty → size → content sniff).
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
        if not data[:5] == b"%PDF-":
            return "This PDF appears to be corrupted or isn't a real PDF. Try re-downloading your statement."
    else:  # csv
        if b"\x00" in head:
            return "This CSV appears to be corrupted or isn't plain text. Please export a fresh CSV from your bank."
        if b"," not in head and b"\n" not in head:
            return "We couldn't find any columns in this CSV. Please upload a bank statement export."
    return ""


def _server_hook_error(name: str) -> str:
    """Simulated server-side outcomes (prototype's filename test hooks). Epic 2 replaces this."""
    n = (name or "").lower()
    if "unsupported" in n:
        return "We don't recognise this statement format yet. Supported: most Indian bank PDF/CSV exports."
    if "servererror" in n:
        return "Our server had a problem processing your file. Please try again in a moment."
    if "network" in n:
        return "Network error — we couldn't reach the server. Check your connection and try again."
    return ""


class UploadState(AuthState):
    """Drives the upload zone, validation errors, and the transparent parse animation."""

    error: str = ""
    filename: str = ""
    parsing: bool = False  # swaps the drop zone for the progress card
    active_step: str = ""  # the step currently spinning
    done_steps: list[str] = []  # completed steps (checked)
    summary_visible: bool = False  # parse summary + enabled CTA

    # Parse results (demo fallback until the Epic 2 parser lands).
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
    async def handle_upload(self, files: list[rx.UploadFile]):
        """Validate the dropped/chosen file, then start the parse animation."""
        self.error = ""
        if not files:
            self.error = "No file selected. Please choose a statement to upload."
            return
        f = files[0]
        name = f.name or getattr(f, "filename", "") or "statement"
        data = await f.read()
        err = validate_statement(name, f.content_type or "", data) or _server_hook_error(name)
        if err:
            self.error = err
            return
        if "parsefail" in name.lower():
            self.error = (
                "We couldn't parse this statement. The file opened but we couldn't extract any "
                "transactions — it may be an unusual or scanned format."
            )
            return
        async for _ in self._run_parse(name):
            yield

    @rx.event
    async def use_sample(self):
        """'Use a sample statement (demo)' — skips file selection and parses the demo data."""
        self.error = ""
        async for _ in self._run_parse("sample-statement.pdf"):
            yield

    async def _run_parse(self, name: str):
        """Advance the four parse steps (~600ms each), then reveal the summary + CTA."""
        self.reset_page()
        self.filename = name
        self.parsing = True
        yield
        for key, _label in PARSE_STEPS:
            self.active_step = key
            yield
            await asyncio.sleep(0.6)
            self.active_step = ""
            self.done_steps = self.done_steps + [key]
            yield
        # Epic 2 integration point: real parser output replaces these demo counts.
        self.total, self.rules, self.ai, self.need_review = (
            _PARSE_TOTAL, _PARSE_RULES, _PARSE_AI, _PARSE_NEED_REVIEW,
        )
        self.summary_visible = True
        yield
