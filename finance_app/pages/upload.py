"""Statement Upload page (Step 1 of 3), rendered to match WDS prototype ``01.3``.

Flow layout (``.page--flow``) with a step indicator + logout, an instruction block, a
drag/drop PDF-or-CSV zone with client + server-style validation, a "use a sample" shortcut,
the transparent parse-progress card, and a Dashboard CTA that stays disabled until parsing
completes. Real statement parsing lands in Epic 2 (see ``upload_state``); the UI is final.
"""

import reflex as rx

from finance_app.state.upload_state import UPLOAD_ID, UploadState


def _topbar() -> rx.Component:
    return rx.el.div(
        rx.el.span("Step 1 of 3", class_name="step-indicator"),
        rx.el.button(
            rx.el.span("⏻", class_name="ico", aria_hidden="true"),
            " Log out",
            on_click=UploadState.logout,
            class_name="logout-btn",
        ),
        class_name="flow-topbar",
    )


def _instructions() -> rx.Component:
    return rx.el.div(
        rx.el.h1("Upload your bank statement", class_name="flow-headline"),
        rx.el.p(
            "We'll read your transactions to build your Safe-to-Spend number. Your file never "
            "leaves your device unencrypted.",
            class_name="flow-subline",
        ),
    )


def _upload_zone() -> rx.Component:
    """Prototype's default (pre-parse) view: drop zone + hint + error + sample link."""
    return rx.fragment(
        rx.upload(
            rx.el.div("☁︎", class_name="cloud", aria_hidden="true"),
            rx.el.p(
                "Tap to choose a PDF or CSV — or drop it here", class_name="zone-label",
            ),
            id=UPLOAD_ID,
            accept={"application/pdf": [".pdf"], "text/csv": [".csv"]},
            max_files=1,
            multiple=False,
            on_drop=UploadState.handle_upload(rx.upload_files(upload_id=UPLOAD_ID)),
            class_name="upload-zone",
            # rx.upload injects its own inline defaults, so restate the .upload-zone base here
            # (the class still drives :hover and the .cloud/.zone-label descendant styles).
            border="2px dashed var(--gray-300)",
            border_radius="var(--radius)",
            background="var(--gray-50)",
            padding="var(--space-xl) var(--space-md)",
            text_align="center",
            cursor="pointer",
            width="100%",
        ),
        rx.el.p(
            "PDF or CSV · Max 10 MB · We support most Indian banks",
            class_name="upload-zone-hint",
        ),
        rx.cond(
            UploadState.error != "",
            rx.el.div(UploadState.error, class_name="upload-error", role="alert"),
        ),
        rx.el.a(
            "Use a sample statement (demo)",
            on_click=UploadState.use_sample,
            class_name="link upload-sample",
            cursor="pointer",
        ),
    )


def _step_row(key: str, label: str, count_text) -> rx.Component:
    is_active = UploadState.active_step == key
    is_done = UploadState.done_steps.contains(key)
    return rx.el.li(
        rx.el.span(rx.cond(is_done, "✓", ""), class_name="step-icon"),
        f" {label} ",
        rx.el.span(rx.cond(is_done, count_text, ""), class_name="step-count"),
        class_name=rx.cond(
            is_active,
            "step-row is-active",
            rx.cond(is_done, "step-row is-done", "step-row"),
        ),
        custom_attrs={"data-step": key},
    )


def _progress_card() -> rx.Component:
    return rx.el.div(
        rx.el.span(
            rx.el.span("📄", aria_hidden="true"),
            " ",
            rx.el.span(UploadState.filename, class_name="fname"),
            class_name="file-chip",
        ),
        rx.el.ul(
            _step_row("read", "Reading your statement", ""),
            _step_row("identify", "Identifying transactions",
                      f"{UploadState.total} transactions found"),
            _step_row("rules", "Categorising with our rules",
                      f"{UploadState.rules} categorised by rules"),
            _step_row("ai", "AI assist for ambiguous ones",
                      f"{UploadState.ai} categorised by AI"),
            class_name="step-list", aria_live="polite",
        ),
        rx.cond(
            UploadState.summary_visible,
            rx.el.div(
                rx.el.h2(f"Parsed {UploadState.total} transactions"),
                rx.el.p(
                    f"{UploadState.rules} by rules · {UploadState.ai} by AI · ",
                    rx.el.strong(f"{UploadState.need_review} need your help"),
                ),
                class_name="parse-summary", aria_live="assertive",
            ),
        ),
        class_name="progress-card",
    )


@rx.page(route="/upload", title="Upload your statement · AI Financial Copilot",
         on_load=[UploadState.check_auth, UploadState.reset_page])
def upload() -> rx.Component:
    return rx.el.main(
        _topbar(),
        _instructions(),
        rx.cond(UploadState.parsing, _progress_card(), _upload_zone()),
        rx.el.div(
            rx.el.button(
                "Go to my Dashboard →",
                disabled=~UploadState.summary_visible,
                on_click=rx.redirect("/dashboard"),
                class_name="btn btn--primary",
            ),
            margin_top="var(--space-lg)",
        ),
        class_name="page--flow",
    )
