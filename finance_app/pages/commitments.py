"""Commitments Management page (Story 5.5 / FR-6.5, FR-9.2) — WDS screen ``02.1``.

A dedicated page, not a Dashboard modal — that is the product decision the epics record, and
the prototype it is ported from. Same DOM shape and class names as
``02.1-commitments-management.html`` so ``assets/wds.css`` styles it unchanged.

The Safe-to-Spend impact bar is ``aria-live="polite"`` so a screen-reader user hears the figure
change after a save, which is the whole point of the page.
"""
from __future__ import annotations

import reflex as rx

from finance_app.components.nav import side_nav
from finance_app.state.commitments_state import (
    CRITICALITY_CHOICES,
    CommitmentsState,
)


def _impact_bar() -> rx.Component:
    """Two engine-computed figures: what's ring-fenced, and what that leaves (FR-9.4)."""
    return rx.el.div(
        rx.el.div(
            rx.el.span("Protecting this month", class_name="commit-impact-label"),
            rx.el.span(CommitmentsState.protecting_total, class_name="commit-impact-amount"),
            class_name="commit-impact-chip",
        ),
        rx.el.div(
            rx.el.span("Safe to spend", class_name="commit-impact-label"),
            rx.el.span(CommitmentsState.safe_to_spend, class_name="commit-impact-amount"),
            class_name="commit-impact-chip",
        ),
        class_name="commit-impact-bar",
        aria_live="polite",
    )


def _suggestion_card(suggestion) -> rx.Component:
    """One auto-detected recurring charge with Protect / Dismiss actions (Story 5.6 / FR-9.1)."""
    return rx.el.li(
        rx.el.span(suggestion.prompt, class_name="commit-suggest-text"),
        rx.el.span(
            rx.el.button(
                "Protect it",
                on_click=CommitmentsState.confirm_suggestion(suggestion.signature),
                class_name="btn btn--primary commit-suggest-confirm",
                type="button",
            ),
            rx.el.button(
                "Not a bill",
                on_click=CommitmentsState.dismiss_suggestion(suggestion.signature),
                class_name="link commit-suggest-dismiss",
                type="button",
            ),
            class_name="commit-suggest-actions",
        ),
        class_name="commit-suggest-row",
    )


def _suggestions() -> rx.Component:
    """"We noticed these recurring charges" panel — only shown when there's something to confirm."""
    return rx.cond(
        CommitmentsState.suggestions,
        rx.el.div(
            rx.el.h2("We noticed these recurring charges", class_name="commit-suggest-title"),
            rx.el.ul(
                rx.foreach(CommitmentsState.suggestions, _suggestion_card),
                class_name="commit-suggest-list",
            ),
            class_name="commit-suggest",
            role="region",
            aria_label="Suggested commitments",
        ),
    )


def _commitment_row(commitment) -> rx.Component:
    """One commitment with per-row Edit / Delete (Story 5.5 AC).

    The prototype puts these behind a "…" popover; two inline buttons carry the same actions
    without a per-row open-state var, and keep both in the tab order.
    """
    return rx.el.li(
        rx.el.span(
            commitment.icon, class_name="commit-row-icon", aria_label=commitment.criticality
        ),
        rx.el.span(
            rx.el.span(commitment.name, class_name="commit-row-name"),
            rx.el.span(commitment.due_label, class_name="commit-row-due"),
            class_name="commit-row-meta",
        ),
        rx.el.span(commitment.amount, class_name="commit-row-amount"),
        rx.el.span(
            rx.el.button(
                "Edit",
                on_click=CommitmentsState.open_edit(commitment.id),
                class_name="commit-row-action",
                aria_label="Edit " + commitment.name,
                type="button",
            ),
            rx.el.button(
                "Delete",
                on_click=CommitmentsState.open_delete(commitment.id),
                class_name="commit-row-action danger",
                aria_label="Delete " + commitment.name,
                type="button",
            ),
            class_name="commit-row-actions",
        ),
        class_name="commit-row",
    )


def _criticality_chip(value: str, label: str, tooltip: str) -> rx.Component:
    is_active = CommitmentsState.form_criticality == value
    return rx.el.button(
        label,
        on_click=CommitmentsState.set_criticality(value),
        class_name=rx.cond(is_active, "chip is-active", "chip"),
        aria_pressed=is_active.to_string(),
        title=tooltip,
        type="button",
    )


def _field(label: str, *children, error) -> rx.Component:
    return rx.el.div(
        rx.el.label(label),
        *children,
        rx.cond(error != "", rx.el.span(error, class_name="error", role="alert")),
        class_name="field",
    )


def _add_edit_modal() -> rx.Component:
    """Add/edit modal *on this page* — name, amount, due-day, criticality (Story 5.5 AC)."""
    return rx.cond(
        CommitmentsState.modal_open,
        rx.el.div(
            rx.el.div(
                rx.el.button(
                    "×",
                    on_click=CommitmentsState.close_modal,
                    class_name="modal-close",
                    aria_label="Close",
                    type="button",
                ),
                rx.el.h3(CommitmentsState.modal_title),
                _field(
                    "Name",
                    rx.el.input(
                        value=CommitmentsState.form_name,
                        on_change=CommitmentsState.set_form_name,
                        placeholder="e.g. Electricity bill, HDFC EMI, Netflix",
                        max_length=50,
                        auto_complete="off",
                    ),
                    error=CommitmentsState.name_error,
                ),
                _field(
                    "Amount",
                    rx.el.input(
                        value=CommitmentsState.form_amount,
                        on_change=CommitmentsState.set_form_amount,
                        type="number",
                        input_mode="numeric",
                        min="1",
                        placeholder="₹0",
                    ),
                    error=CommitmentsState.amount_error,
                ),
                _field(
                    "Due day of the month",
                    rx.el.input(
                        value=CommitmentsState.form_due_day,
                        on_change=CommitmentsState.set_form_due_day,
                        type="number",
                        min="1",
                        max="31",
                        placeholder="e.g. 15",
                    ),
                    error=CommitmentsState.due_day_error,
                ),
                rx.el.div(
                    rx.el.label("How critical is this?"),
                    rx.el.div(
                        *[
                            _criticality_chip(value, label, tooltip)
                            for value, label, tooltip in CRITICALITY_CHOICES
                        ],
                        class_name="chip-group chip--wrap",
                    ),
                    class_name="field",
                ),
                rx.el.div(
                    rx.el.button(
                        CommitmentsState.save_label,
                        on_click=CommitmentsState.save_commitment,
                        class_name="btn btn--primary",
                        # aria-disabled, not disabled: the button stays focusable (NFR-8).
                        aria_disabled=CommitmentsState.saving.to_string(),
                        type="button",
                    ),
                ),
                class_name="modal modal--commit",
            ),
            class_name="modal-overlay",
            role="dialog",
            aria_modal="true",
        ),
    )


def _delete_modal() -> rx.Component:
    return rx.cond(
        CommitmentsState.delete_open,
        rx.el.div(
            rx.el.div(
                rx.el.h3("Remove this commitment?"),
                rx.el.p(CommitmentsState.delete_prompt, class_name="text-muted"),
                rx.el.div(
                    rx.el.button(
                        "Cancel",
                        on_click=CommitmentsState.close_delete,
                        class_name="btn btn--secondary",
                        type="button",
                    ),
                    rx.el.button(
                        "Remove",
                        on_click=CommitmentsState.confirm_delete,
                        class_name="btn btn--primary",
                        type="button",
                    ),
                    style={"display": "flex", "gap": "0.5rem"},
                ),
                class_name="modal",
            ),
            class_name="modal-overlay",
            role="dialog",
            aria_modal="true",
        ),
    )


@rx.page(
    route="/commitments",
    title="Commitments · Finance Analyzer",
    on_load=[CommitmentsState.check_auth, CommitmentsState.load_commitments_page],
)
def commitments() -> rx.Component:
    return rx.fragment(
        # The sidebar has no Commitments tab by design (FR-6.4): this page is reached from the
        # Dashboard. "dashboard" stays the active tab so the user keeps their bearings.
        side_nav("dashboard"),
        rx.el.main(
            rx.el.div(
                rx.el.div(
                    rx.el.a(
                        rx.el.svg(
                            rx.el.path(d="M19 12H5M12 19l-7-7 7-7"),
                            view_box="0 0 24 24",
                            fill="none",
                            stroke="currentColor",
                            stroke_width="2.25",
                            stroke_linecap="round",
                            stroke_linejoin="round",
                            class_name="commit-back-icon",
                        ),
                        href="/dashboard",
                        class_name="commit-back-arrow",
                        aria_label="Back to Dashboard",
                    ),
                    rx.el.h1("Commitments", class_name="commit-page-title"),
                    class_name="commit-title-row",
                ),
                _impact_bar(),
                _suggestions(),
                rx.cond(
                    CommitmentsState.empty,
                    rx.el.div(
                        "No commitments yet. Add your recurring bills and EMIs so they're "
                        "always protected.",
                        class_name="commit-empty",
                    ),
                    rx.el.ul(
                        rx.foreach(CommitmentsState.commitments, _commitment_row),
                        class_name="commit-list",
                    ),
                ),
                rx.el.div(
                    rx.el.button(
                        "+ Add a commitment",
                        on_click=CommitmentsState.open_add,
                        class_name="btn btn--primary",
                        type="button",
                    ),
                ),
                class_name="commit-content",
            ),
            class_name="dash has-sidenav",
        ),
        _add_edit_modal(),
        _delete_modal(),
        rx.cond(
            CommitmentsState.toast != "",
            rx.el.div(CommitmentsState.toast, class_name="toast", role="status"),
        ),
    )
