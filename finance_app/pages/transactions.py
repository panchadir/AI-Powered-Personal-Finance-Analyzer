"""Transactions page (Story 3.1), rebuilt against WDS prototype ``01.4-transactions-table.html``.

Reuses the prototype's exact class names (served via ``assets/wds.css``) so this page stays
visually consistent with the approved WDS baseline: ``.txn-header-row``, ``.pill-btn``,
``.banner`` (amber needs-review banner), ``.chip-group.chip--wrap``/``.chip``, ``.txn-list``/
``.txn-row``, ``.txn-amount.is-credit`` (green credit rows, UX-DR14), ``.txn-badge--review``.

Out of scope for this story (see Story 3.1 Dev Notes): the Teach Me correction panel
(Story 3.3) and the full confidence-threshold badge system (Story 3.4). Rows render as
static, non-interactive list items — not focusable buttons — until Story 3.3 gives them
real click behavior (a code-review follow-up: a focusable control with no ``on_click`` is a
dead end for keyboard/screen-reader users).
"""

import reflex as rx

from finance_app.components.nav import side_nav
from finance_app.state.transactions_state import ChipItem, TransactionsState, TxnRow


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


def _row(row: TxnRow) -> rx.Component:
    return rx.el.li(
        rx.el.div(
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
                rx.el.span(class_name="txn-badge txn-badge--none", aria_hidden="true"),
            ),
            class_name="txn-row",
        ),
        role="listitem",
        key=row.id.to(str),
    )


def _empty_state() -> rx.Component:
    return rx.el.div(
        "Upload a statement and your transactions will show up here.",
        class_name="text-muted",
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
            class_name="page--flow has-sidenav",
        ),
    )
