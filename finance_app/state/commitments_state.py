"""Commitments page state (Story 5.5 / FR-9) — list, add, edit, delete, live Safe-to-Spend.

Every mutation follows the same shape, and the order matters:

    validate → write the commitment row → call ``services/engine/`` → persist the score →
    yield the updated UI

There is **no inline Safe-to-Spend arithmetic in this file** (AD-1 / NFR-3). The impact bar's
figures come back from the engine via ``engine_bridge.compute_dashboard`` — the same call the
Dashboard hero makes — so the two screens cannot drift (FR-4.10, FR-9.4). That shared call is
what makes "the Dashboard reflects the new figure when next rendered" true by construction,
rather than by remembering to update two places.

Every read and write is filtered by ``user_id`` (AD-4). A commitment id that doesn't belong to
the signed-in user is treated as absent, not as an error to report — an attacker learns nothing
from the response.
"""
from __future__ import annotations

import dataclasses
import logging
from decimal import Decimal, InvalidOperation

import reflex as rx

from finance_app.models import Commitment, CommitmentSuggestion
from finance_app.state.auth_state import LOGIN_ROUTE, AuthState, user_for_token
from finance_app.state.engine_bridge import (
    compute_dashboard,
    detect_commitment_candidates,
    format_money,
    load_commitments,
    sync_confidence_score,
)
from services.engine import due_day_label
from services.utils.enums import CRITICALITY_DEFAULT, Criticality

log = logging.getLogger(__name__)

MAX_NAME_LENGTH = 50

#: Criticality tiers, in the prototype's order, with the tooltip copy from WDS 02.1. The
#: proximity windows (7d / 5d / 3d) live in the engine — the UI only names the tier.
CRITICALITY_CHOICES: tuple[tuple[str, str, str], ...] = (
    (
        Criticality.critical.value,
        "Critical",
        "EMIs, rent, loan repayments — missing this would have serious consequences",
    ),
    (
        Criticality.important.value,
        "Important",
        "Regular bills, subscriptions — missing this would be inconvenient",
    ),
    (
        Criticality.flexible.value,
        "Flexible",
        "Savings, gym memberships — you'd prefer to pay but it's not an emergency",
    ),
)

_CRIT_ICONS = {"critical": "🔴", "important": "🟠", "flexible": "⚪"}


@dataclasses.dataclass
class CommitmentView:
    """One row of the commitments list. Display strings only — no ``Decimal`` crosses the wire."""

    id: int = 0
    name: str = ""
    amount: str = ""  # formatINR'd
    due_label: str = ""  # "Due end of month" / "Due 15th of every month"
    criticality: str = ""
    icon: str = ""


@dataclasses.dataclass
class SuggestionView:
    """One auto-detected recurring charge awaiting the user's confirm/dismiss (Story 5.6)."""

    signature: str = ""
    prompt: str = ""  # "We noticed a recurring ₹8,500 charge around the 5th each month…"


def _due_phrase(due_day: int) -> str:
    """Natural-language cadence for a suggestion prompt (distinct from the list's ``Due …``)."""
    if due_day == 31:
        return "at the end of each month"
    suffix = {1: "st", 2: "nd", 3: "rd", 21: "st", 22: "nd", 23: "rd"}.get(due_day, "th")
    return f"around the {due_day}{suffix} each month"


def as_text(value: object) -> str:
    """Normalize a form value to text.

    An ``<input type="number">`` may deliver its value as a float, so a due-day of 15 can
    arrive as ``15.0``. ``int("15.0")`` raises, which would reject a perfectly valid day. Whole
    floats are rendered without the trailing ``.0`` before parsing.
    """
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def validate_commitment(
    name: object, amount_raw: object, due_day_raw: object
) -> tuple[dict[str, str], str, Decimal, int]:
    """Validate the add/edit form. Returns ``(errors, name, amount, due_day)``.

    Pure and framework-free so the rules are unit-testable without a Reflex app. On any error
    the returned values are placeholders — the caller must check ``errors`` first. Nothing is
    coerced past a validation failure: a commitment saved with a silently-wrong amount would
    under-reserve money the user is counting on (NFR-1).
    """
    errors: dict[str, str] = {}

    name = as_text(name)
    if not name:
        errors["name"] = "Please name this commitment"
    elif len(name) > MAX_NAME_LENGTH:
        errors["name"] = f"Keep the name under {MAX_NAME_LENGTH} characters"

    amount = Decimal("0")
    try:
        amount = Decimal(as_text(amount_raw))
        if not amount.is_finite() or amount <= 0:
            errors["amount"] = "Amount must be greater than ₹0"
    except (InvalidOperation, ValueError, TypeError):
        errors["amount"] = "Amount must be greater than ₹0"

    due_day = 0
    try:
        # Parsed as Decimal so "15.0" is accepted but "15.5" is refused — a fractional day of
        # the month is not a typo we should guess at.
        parsed = Decimal(as_text(due_day_raw))
        if parsed != parsed.to_integral_value() or not 1 <= parsed <= 31:
            errors["due_day"] = "Due day must be between 1 and 31"
        else:
            due_day = int(parsed)
    except (InvalidOperation, ValueError, TypeError):
        errors["due_day"] = "Due day must be between 1 and 31"

    return errors, name, amount, due_day


class CommitmentsState(AuthState):
    """Drives the Commitments Management page (WDS screen 02.1)."""

    commitments: list[CommitmentView] = []
    protecting_total: str = "₹0"
    safe_to_spend: str = "₹0"
    empty: bool = True

    # Auto-detected recurring charges awaiting confirm/dismiss (Story 5.6 / FR-9.1).
    suggestions: list[SuggestionView] = []

    # Add/edit modal
    modal_open: bool = False
    editing_id: int = -1  # -1 == adding
    modal_title: str = "What's this commitment?"
    save_label: str = "Protect this commitment"
    form_name: str = ""
    form_amount: str = ""
    form_due_day: str = ""
    form_criticality: str = CRITICALITY_DEFAULT.value
    name_error: str = ""
    amount_error: str = ""
    due_day_error: str = ""
    saving: bool = False

    # Delete confirmation
    delete_open: bool = False
    delete_id: int = -1
    delete_prompt: str = ""

    toast: str = ""

    # ---- Loading ----

    @rx.event
    def load_commitments_page(self):
        """Page ``on_load``: list the commitments and compute the impact bar from the engine."""
        with rx.session() as session:
            user = user_for_token(session, self.auth_token)
            if user is None:
                return rx.redirect(LOGIN_ROUTE)
            self._refresh(session, user.id)

    def _refresh(self, session, user_id: int) -> None:
        """Re-read rows and re-run the engine. The single place the impact bar is populated."""
        rows = load_commitments(session, user_id)
        self.commitments = [
            CommitmentView(
                id=row.id,
                name=row.name,
                amount=format_money(Decimal(row.amount)),
                due_label=f"Due {due_day_label(row.due_day)}",
                criticality=row.criticality,
                icon=_CRIT_ICONS.get(row.criticality, "⚪"),
            )
            for row in rows
        ]
        self.empty = not self.commitments

        data = compute_dashboard(session, user_id)
        # Both figures are engine output. `reserved_total` is what is actually ring-fenced this
        # cycle — not the naive sum of every commitment, which would over-report protection for
        # bills falling after the next payday.
        self.protecting_total = format_money(data.evidence.reserved_total)
        self.safe_to_spend = format_money(data.evidence.safe_to_spend_today)

        # Recurring charges we spotted that aren't yet commitments (Story 5.6). Signatures the
        # user already confirmed or dismissed are excluded by the detector, so this list only
        # ever holds genuinely-open suggestions.
        self.suggestions = [
            SuggestionView(
                signature=c.signature,
                prompt=(
                    f"We noticed a recurring {format_money(c.amount)} charge to "
                    f"{c.merchant} {_due_phrase(c.due_day)}. Protect it as a commitment?"
                ),
            )
            for c in detect_commitment_candidates(session, user_id)
        ]

    # ---- Modal ----

    @rx.event
    def open_add(self):
        self.editing_id = -1
        self.modal_title = "What's this commitment?"
        self.save_label = "Protect this commitment"
        self.form_name = self.form_amount = self.form_due_day = ""
        self.form_criticality = CRITICALITY_DEFAULT.value  # FR-4.3: defaults to Important
        self._clear_errors()
        self.modal_open = True

    @rx.event
    def open_edit(self, commitment_id: int):
        with rx.session() as session:
            user = user_for_token(session, self.auth_token)
            if user is None:
                return rx.redirect(LOGIN_ROUTE)
            row = self._owned(session, user.id, commitment_id)
            if row is None:
                return
            self.editing_id = row.id
            self.modal_title = "Edit commitment"
            self.save_label = "Save changes"
            self.form_name = row.name
            self.form_amount = str(Decimal(row.amount))
            self.form_due_day = str(row.due_day)
            self.form_criticality = row.criticality
        self._clear_errors()
        self.modal_open = True

    @rx.event
    def close_modal(self):
        self.modal_open = False
        self.editing_id = -1
        self._clear_errors()

    @rx.event
    def set_criticality(self, value: str):
        self.form_criticality = value

    @rx.event
    def set_form_name(self, value: str):
        self.form_name = value
        self.name_error = ""

    # The amount and due-day inputs are `type="number"`, whose on_change Reflex types as float.
    # Accepting both and normalizing through `as_text` keeps "15" and 15.0 equivalent, and
    # clears the error as the user types (the clear-on-input rule the auth forms already follow).
    @rx.event
    def set_form_amount(self, value: str | float):
        self.form_amount = as_text(value)
        self.amount_error = ""

    @rx.event
    def set_form_due_day(self, value: str | float):
        self.form_due_day = as_text(value)
        self.due_day_error = ""

    def _clear_errors(self) -> None:
        self.name_error = self.amount_error = self.due_day_error = ""

    def _owned(self, session, user_id: int, commitment_id: int) -> Commitment | None:
        """Fetch a commitment **only** if it belongs to this user (AD-4 / IDOR guard)."""
        row = session.get(Commitment, commitment_id)
        return row if row is not None and row.user_id == user_id else None

    # ---- Save (add or edit) ----

    @rx.event
    def save_commitment(self):
        """Validate → write the row → run the engine → persist the score → update the bar."""
        errors, name, amount, due_day = validate_commitment(
            self.form_name, self.form_amount, self.form_due_day
        )
        self.name_error = errors.get("name", "")
        self.amount_error = errors.get("amount", "")
        self.due_day_error = errors.get("due_day", "")
        if errors:
            return

        self.saving = True
        try:
            with rx.session() as session:
                user = user_for_token(session, self.auth_token)
                if user is None:
                    return rx.redirect(LOGIN_ROUTE)

                if self.editing_id >= 0:
                    row = self._owned(session, user.id, self.editing_id)
                    if row is None:
                        self.toast = "That commitment is no longer there."
                        return
                    row.name, row.amount, row.due_day = name, amount, due_day
                    row.criticality = self.form_criticality
                    session.add(row)
                    trigger, message = "commitment_edited", f"Updated {name}"
                else:
                    session.add(
                        Commitment(  # type: ignore[call-arg]
                            user_id=user.id,
                            name=name,
                            amount=amount,
                            due_day=due_day,
                            criticality=self.form_criticality,
                        )
                    )
                    trigger = "commitment_added"
                    message = f"Protected {format_money(amount)} for {name} — Safe-to-Spend updated"
                session.commit()

                # Engine first, then persist the score with its explanation, then refresh the
                # bar from that same computation. No figure here is computed by this handler.
                data = compute_dashboard(session, user.id)
                sync_confidence_score(session, user.id, data.evidence, trigger_event=trigger)
                self._refresh(session, user.id)

            self.toast = message
            self.modal_open = False
            self.editing_id = -1
        finally:
            self.saving = False

    # ---- Delete ----

    @rx.event
    def open_delete(self, commitment_id: int):
        with rx.session() as session:
            user = user_for_token(session, self.auth_token)
            if user is None:
                return rx.redirect(LOGIN_ROUTE)
            row = self._owned(session, user.id, commitment_id)
            if row is None:
                return
            self.delete_id = row.id
            self.delete_prompt = f"Remove {row.name}? Your Safe-to-Spend will update."
        self.delete_open = True

    @rx.event
    def close_delete(self):
        self.delete_open = False
        self.delete_id = -1

    @rx.event
    def confirm_delete(self):
        if self.delete_id < 0:
            return
        with rx.session() as session:
            user = user_for_token(session, self.auth_token)
            if user is None:
                return rx.redirect(LOGIN_ROUTE)
            row = self._owned(session, user.id, self.delete_id)
            if row is None:
                self.delete_open = False
                self.delete_id = -1
                return
            name = row.name
            session.delete(row)
            session.commit()

            data = compute_dashboard(session, user.id)
            sync_confidence_score(
                session, user.id, data.evidence, trigger_event="commitment_deleted"
            )
            self._refresh(session, user.id)

        self.toast = f"Removed {name} — Safe-to-Spend updated"
        self.delete_open = False
        self.delete_id = -1

    # ---- Auto-detected suggestions (Story 5.6) ----

    @rx.event
    def confirm_suggestion(self, signature: str):
        """Turn a detected recurring charge into a real commitment (FR-9.1).

        Re-runs the detector server-side and matches by signature rather than trusting the
        client for the amount/due-day — the confirmed figure is one the engine derived, never
        one posted from the browser. Records the signature as ``confirmed`` so it is never
        proposed again, then recomputes Safe-to-Spend exactly like a manual add.
        """
        with rx.session() as session:
            user = user_for_token(session, self.auth_token)
            if user is None:
                return rx.redirect(LOGIN_ROUTE)

            candidate = next(
                (c for c in detect_commitment_candidates(session, user.id)
                 if c.signature == signature),
                None,
            )
            if candidate is None:
                # Already decided, or the pattern no longer holds — refresh and move on.
                self._refresh(session, user.id)
                return

            session.add(
                Commitment(  # type: ignore[call-arg]
                    user_id=user.id,
                    name=candidate.merchant,
                    amount=candidate.amount,
                    due_day=candidate.due_day,
                    criticality=candidate.criticality,
                )
            )
            session.add(
                CommitmentSuggestion(  # type: ignore[call-arg]
                    user_id=user.id, signature=signature, status="confirmed"
                )
            )
            session.commit()

            data = compute_dashboard(session, user.id)
            sync_confidence_score(
                session, user.id, data.evidence, trigger_event="commitment_auto_confirmed"
            )
            self._refresh(session, user.id)

        self.toast = f"Protected {candidate.merchant} — Safe-to-Spend updated"

    @rx.event
    def dismiss_suggestion(self, signature: str):
        """Record a suggestion as dismissed so the detector never re-surfaces it (FR-9.1)."""
        with rx.session() as session:
            user = user_for_token(session, self.auth_token)
            if user is None:
                return rx.redirect(LOGIN_ROUTE)
            session.add(
                CommitmentSuggestion(  # type: ignore[call-arg]
                    user_id=user.id, signature=signature, status="dismissed"
                )
            )
            session.commit()
            self._refresh(session, user.id)

    @rx.event
    def dismiss_toast(self):
        self.toast = ""
