"""Transactions page (Story 3.1; interactive rows + Teach Me panel added in Story 3.3;
3-state confidence badge added in Story 3.4), rebuilt against WDS prototype
``01.4-transactions-table.html``.

Reuses the prototype's exact class names (served via ``assets/wds.css``) so this page stays
visually consistent with the approved WDS baseline: ``.txn-header-row``, ``.pill-btn``,
``.banner`` (amber needs-review banner), ``.chip-group.chip--wrap``/``.chip``, ``.txn-list``/
``.txn-row``, ``.txn-amount.is-credit`` (green credit rows, UX-DR14), ``.txn-badge--review``/
``.txn-badge--ai`` (Story 3.4 — the class already existed in ``wds.css``, unused until now),
``.teach-me``/``.teach-me-label``/``.toggle-row``/``.switch`` (the correction panel).

Story 3.3 note: the whole row is clickable to open the Teach Me panel (not just the badge) —
the WDS prototype's own click handler is on the entire ``.txn-row``, and per project-context's
WDS-precedence rule that's what this page follows, even though epics.md's Story 3.3 AC prose
says "click a transaction's category badge." Same resolution pattern as prior epics-vs-WDS
wording gaps (Stories 1.3/1.4/3.1).

Story 3.4 note: the list itself intentionally stays a plain ``rx.foreach`` over every row —
no virtual scroll. epics.md's AC asks for it, but the WDS prototype renders a full plain list
with no virtualization at any row count, and the project's own UX-scenario notes for this
screen had already flagged virtual scroll as likely unnecessary on this desktop-only MVP.
User decision (2026-07-10): skip it here, tracked as a real future improvement in
``deferred-work.md``, not a dropped requirement.
"""

import reflex as rx

from finance_app.components.nav import side_nav
from finance_app.components.skeleton import txn_skeleton
from finance_app.state.transactions_state import (
    CategoryOption,
    ChipItem,
    TransactionsState,
    TxnRow,
)


def _chip(item: ChipItem) -> rx.Component:
    return rx.el.button(
        item.label,
        on_click=TransactionsState.set_filter(item.key),
        class_name=rx.cond(
            TransactionsState.active_filter == item.key, "chip is-active", "chip"
        ),
        type="button",
        role="tab",
        key=item.key,
    )


def _category_chip(option: CategoryOption) -> rx.Component:
    return rx.el.button(
        option.category,
        on_click=TransactionsState.select_category(option.category),
        class_name=rx.cond(option.is_selected, "chip is-active", "chip"),
        type="button",
        aria_pressed=rx.cond(option.is_selected, "true", "false"),
        key=option.category,
    )


def _teach_me_panel(row: TxnRow) -> rx.Component:
    """Mirrors the WDS prototype's ``buildTeachMe`` markup/classes exactly."""
    return rx.el.div(
        rx.el.p("What's this actually for?", class_name="teach-me-label"),
        rx.el.div(
            rx.foreach(TransactionsState.category_options, _category_chip),
            class_name="chip-group chip--wrap",
        ),
        rx.el.div(
            rx.el.span(f"Apply this to all ‘{row.merchant}’ transactions?"),
            rx.el.label(
                rx.el.input(
                    type="checkbox",
                    checked=TransactionsState.reapply,
                    on_change=TransactionsState.toggle_reapply,
                ),
                rx.el.span(class_name="track"),
                class_name="switch",
            ),
            class_name="toggle-row",
        ),
        rx.el.button(
            "Got it — save this",
            on_click=TransactionsState.save_correction,
            class_name="btn btn--secondary",
            type="button",
            disabled=TransactionsState.selected_category == "",
        ),
        class_name="teach-me",
        id=f"teach-me-panel-{row.id}",
    )


def _row(row: TxnRow) -> rx.Component:
    is_open = TransactionsState.open_row_id == row.id
    return rx.el.li(
        rx.el.button(
            rx.el.span(row.icon, class_name="txn-icon", aria_hidden="true"),
            rx.el.span(
                rx.el.span(row.merchant, class_name="txn-merchant"),
                rx.el.span(f"{row.category} · {row.date_label}", class_name="txn-cat-date"),
                class_name="txn-meta",
            ),
            rx.el.span(
                row.amount_label,
                class_name=rx.cond(row.is_credit, "txn-amount is-credit", "txn-amount"),
            ),
            rx.cond(
                row.needs_review,
                rx.el.span("?", class_name="txn-badge txn-badge--review", aria_label="Needs review"),
                rx.cond(
                    row.is_ai,
                    rx.el.span("AI", class_name="txn-badge txn-badge--ai", aria_label="AI-categorised"),
                    rx.el.span(class_name="txn-badge txn-badge--none", aria_hidden="true"),
                ),
            ),
            on_click=TransactionsState.toggle_row(row.id),
            class_name="txn-row",
            type="button",
            aria_expanded=rx.cond(is_open, "true", "false"),
            aria_controls=f"teach-me-panel-{row.id}",
        ),
        rx.cond(is_open, _teach_me_panel(row)),
        role="listitem",
        key=row.id.to(str),
    )


def _empty_state() -> rx.Component:
    return rx.el.div(
        rx.el.p(
            "Your transactions will appear here after you upload a statement.",
            class_name="text-muted",
        ),
        rx.el.a("Upload your statement", href="/upload", class_name="link"),
        class_name="empty-state",
    )


@rx.page(
    route="/transactions",
    title="Transactions · Finance Analyzer",
    on_load=[TransactionsState.check_auth, TransactionsState.load_transactions],
)
def transactions() -> rx.Component:
    return rx.fragment(
        side_nav("transactions"),
        rx.el.main(
            rx.el.div(
                rx.el.h1("Your transactions", class_name="flow-headline"),
                rx.el.a(
                    "See my Dashboard ",
                    rx.el.span("→", aria_hidden="true"),
                    href="/dashboard",
                    class_name="pill-btn",
                ),
                class_name="txn-header-row",
            ),
            rx.cond(
                TransactionsState.review_count > 0,
                rx.el.div(
                    rx.el.span(class_name="dot", aria_hidden="true"),
                    rx.el.span(
                        rx.el.strong(TransactionsState.review_count),
                        " transactions need your help — we weren't sure how to categorise them",
                    ),
                    class_name="banner",
                    role="status",
                ),
            ),
            rx.cond(
                TransactionsState.confirmation != "",
                rx.el.div(TransactionsState.confirmation, class_name="toast", role="status"),
            ),
            rx.cond(
                TransactionsState.loaded,
                rx.cond(
                    TransactionsState.has_transactions,
                    rx.fragment(
                        rx.el.div(
                            rx.foreach(TransactionsState.chip_items, _chip),
                            class_name="chip-group chip--wrap",
                            role="tablist",
                            aria_label="Filter transactions",
                        ),
                        rx.el.ul(
                            rx.foreach(TransactionsState.visible_rows, _row),
                            class_name="txn-list",
                            role="list",
                        ),
                    ),
                    _empty_state(),
                ),
                # Still loading → skeleton, never the "upload a statement" empty state.
                txn_skeleton(),
            ),
            class_name="page--flow has-sidenav",
        ),
    )
