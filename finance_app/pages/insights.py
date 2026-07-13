"""Insights page — two bands (wins + warnings), evidence blocks, dismiss lifecycle.

Ported from the WDS prototype ``01.6-ai-insights-recommendations.html``: same class names,
same card anatomy (head → observation → evidence block → prose → actions). The evidence block
is the prototype's ``.evidence-block``, already styled in ``assets/wds.css``.

**The win band (2026-07-12).** All five FR-8.1 detectors are negative-valence — the feed was
structurally incapable of telling a user they had improved, and a user who fixed their
spending was rewarded with an empty page. The engine now also emits ``tone="win"`` candidates;
they get their own band *above* the warnings rather than being interleaved, because a win
buried under three criticals does not read as good news, which is the entire reason those
detectors exist.

Divergences from the prototype (Story 7.3 Dev Notes): the footer uses the PRD/epics exact
copy, not the prototype's placeholder; dismiss persists to the DB rather than being the
prototype's client-side fade toggle. Severity badges and the win band are new CSS, built from
existing ``:root`` tokens.
"""
from __future__ import annotations

import reflex as rx

from finance_app.components.nav import side_nav
from finance_app.state.insights_state import (
    EMPTY_COPY,
    FOOTER_NOTE,
    INSUFFICIENT_DATA_COPY,
    WATCH_HEADING,
    WINS_HEADING,
    InsightsState,
)


def _evidence_block(card: rx.Var) -> rx.Component:
    """FR-8.2: 2–3 exact data points — real dates, merchants, amounts — visually distinct.

    Rendered only when the card actually has evidence. Two cards legitimately have none: one
    whose evidence pack was unparseable, and "Spending pace improved", whose claim is about a
    *rate* — no single transaction is evidence for a rate. Both degrade to a card without the
    block, never to an empty grey box.
    """
    return rx.cond(
        card.evidence.length() > 0,
        rx.el.div(
            rx.el.ul(
                rx.foreach(card.evidence, lambda line: rx.el.li(line)),
            ),
            class_name="evidence-block",
            id="insight-evidence-" + card.id.to_string(),
        ),
    )


def _card_actions(card: rx.Var) -> rx.Component:
    return rx.el.div(
        rx.el.button(
            "Dismiss",
            on_click=InsightsState.dismiss(card.id),
            class_name="insight-dismiss",
            aria_label="Dismiss: " + card.pattern_name,
            type="button",
        ),
        rx.el.a(
            "Ask the Copilot about this",
            href=card.copilot_href,
            class_name="btn btn--secondary",
        ),
        class_name="insight-actions",
    )


def _insight_card(card: rx.Var) -> rx.Component:
    """A warning card — the full O→E→E→A prose, severity badge, evidence, both actions."""
    return rx.el.article(
        rx.el.div(
            rx.el.span(card.icon, class_name="insight-icon", aria_hidden="true"),
            rx.el.h2(card.pattern_name, class_name="insight-name"),
            rx.el.span(
                card.severity_label,
                class_name="insight-severity insight-severity--" + card.severity,
            ),
            class_name="insight-card-head",
        ),
        rx.el.p(card.observation, class_name="insight-observation"),
        _evidence_block(card),
        rx.el.p(card.explanation, class_name="insight-explanation"),
        rx.el.p(card.effect, class_name="insight-explanation"),
        rx.el.p(card.advice, class_name="insight-explanation"),
        _card_actions(card),
        class_name="insight-card",
        role="article",
        id="insight-" + card.id.to_string(),  # Story 7.4: Dashboard teaser scroll target
    )


def _win_card(card: rx.Var) -> rx.Component:
    """A win card. Deliberately lighter than a warning: observation + effect + evidence, no
    severity badge (a win has no urgency to rank) and no Explanation paragraph.

    A win does not need a hypothesis for *why* it happened — the user already knows, they did
    it. Repeating the full four-paragraph warning anatomy here would make good news feel as
    heavy as bad news, which is the opposite of the point. Both actions stay, because a win is
    still dismissible and still worth asking the Copilot about.
    """
    return rx.el.article(
        rx.el.div(
            rx.el.span(card.icon, class_name="insight-icon", aria_hidden="true"),
            rx.el.h2(card.pattern_name, class_name="insight-name"),
            class_name="insight-card-head",
        ),
        rx.el.p(card.observation, class_name="insight-observation"),
        _evidence_block(card),
        rx.el.p(card.effect, class_name="insight-explanation"),
        _card_actions(card),
        class_name="insight-card insight-card--win",
        role="article",
        id="insight-" + card.id.to_string(),
    )


def _section_head(heading: str, count_var: rx.Var, element_id: str) -> rx.Component:
    return rx.el.div(
        rx.el.h2(heading, class_name="insights-section-title"),
        rx.el.span(count_var.to_string(), class_name="insights-section-count"),
        class_name="insights-section-head",
        id=element_id,
    )


def _wins_band() -> rx.Component:
    """The good news, above the warnings. Only ever rendered when there is some."""
    return rx.cond(
        InsightsState.win_count > 0,
        rx.el.section(
            _section_head(WINS_HEADING, InsightsState.win_count, "insights-wins-head"),
            rx.el.div(
                rx.foreach(InsightsState.win_cards, _win_card),
                class_name="insights-list",
                id="insights-wins-list",
            ),
            class_name="insights-wins",
        ),
    )


def _watch_band() -> rx.Component:
    """The warnings. The heading only appears when there is also a win band to distinguish it
    from — a lone list of warnings needs no label, it is just "what we noticed"."""
    return rx.cond(
        InsightsState.watch_count > 0,
        rx.el.section(
            rx.cond(
                InsightsState.win_count > 0,
                _section_head(
                    WATCH_HEADING, InsightsState.watch_count, "insights-watch-head"
                ),
            ),
            rx.el.div(
                rx.foreach(InsightsState.cards, _insight_card),
                class_name="insights-list",
                id="insights-list",
            ),
            class_name="insights-watch",
        ),
    )


def _summary() -> rx.Component:
    """A one-glance answer to "is any of this urgent?" before reading a single card."""
    return rx.cond(
        InsightsState.has_anything,
        rx.el.div(
            rx.el.span(
                InsightsState.watch_count.to_string() + " to review",
                class_name="insights-chip",
            ),
            rx.cond(
                InsightsState.needs_attention_count > 0,
                rx.el.span(
                    InsightsState.needs_attention_count.to_string() + " needs attention",
                    class_name="insights-chip insights-chip--alert",
                ),
            ),
            rx.cond(
                InsightsState.win_count > 0,
                rx.el.span(
                    InsightsState.win_count.to_string() + " going well",
                    class_name="insights-chip insights-chip--good",
                ),
            ),
            class_name="insights-summary",
            id="insights-summary",
        ),
    )


def _skeleton() -> rx.Component:
    """Shown while the detectors run and the narrator writes (several sequential LLM calls on
    a cold feed). The page previously rendered an empty ``div`` here, so a slow load looked
    identical to "we found nothing about you" — the single most discouraging thing this page
    could say to someone who just uploaded a statement."""
    return rx.el.div(
        *[
            rx.el.div(
                rx.el.div(class_name="insight-skeleton-line insight-skeleton-line--title"),
                rx.el.div(class_name="insight-skeleton-line"),
                rx.el.div(class_name="insight-skeleton-line insight-skeleton-line--short"),
                class_name="insight-card insight-skeleton",
                aria_hidden="true",
            )
            for _ in range(3)
        ],
        rx.el.p("Looking for patterns in your statement…", class_name="insights-subline"),
        class_name="insights-list",
        id="insights-skeleton",
        role="status",
        aria_live="polite",
    )


def _empty_state() -> rx.Component:
    """FR-8.4: graceful copy, never a blank page or a "No insights" placeholder tone.

    Two arms, because an empty feed means opposite things depending on why it's empty: a user
    with too little history is told the app isn't ready yet; a user who has read and dismissed
    everything is told they're done.

    The upload link rides the "not ready" arm only: telling a user who has read every insight
    to go upload more is a non-sequitur. ``insufficient_data`` (not ``has_data``) gates it
    because it is the finer signal — zero transactions is always insufficient, but a handful
    of transactions is too, and both users need the same nudge.
    """
    return rx.el.div(
        rx.el.p(
            rx.cond(InsightsState.insufficient_data, INSUFFICIENT_DATA_COPY, EMPTY_COPY),
            class_name="insights-subline",
            id="insights-empty",
        ),
        rx.cond(
            InsightsState.insufficient_data,
            rx.el.a("Upload your statement", href="/upload", class_name="link"),
        ),
        class_name="empty-state",
    )


def _footer() -> rx.Component:
    return rx.cond(
        InsightsState.show_footer_note,
        rx.el.div(rx.el.p(FOOTER_NOTE, id="insights-footer-note"), class_name="insights-footer"),
    )


def _dismissed_card(card: rx.Var) -> rx.Component:
    """A read-only echo of a dismissed insight — no Dismiss, no Copilot handoff.

    The user already acted on this one; re-offering the same two buttons would invite them to
    dismiss what is already dismissed. It stays legible (observation + evidence) so the
    section is a record of what was said, not just a list of titles.
    """
    return rx.el.article(
        rx.el.div(
            rx.el.span(card.icon, class_name="insight-icon", aria_hidden="true"),
            rx.el.h3(card.pattern_name, class_name="insight-name"),
            class_name="insight-card-head",
        ),
        rx.el.p(card.observation, class_name="insight-observation"),
        _evidence_block(card),
        class_name="insight-card is-dismissed",  # the prototype's existing soft-fade rule
        role="article",
    )


def _dismissed_section() -> rx.Component:
    """FR-8.4: dismissed insights move to a collapsed section — they don't disappear."""
    return rx.cond(
        InsightsState.dismissed_count > 0,
        rx.el.section(
            rx.el.button(
                rx.el.span("Dismissed (" + InsightsState.dismissed_count.to_string() + ")"),
                rx.el.span(
                    rx.cond(InsightsState.show_dismissed, "Hide", "Show"),
                    class_name="insights-dismissed-action",
                ),
                on_click=InsightsState.toggle_dismissed,
                class_name="insights-dismissed-toggle",
                aria_expanded=InsightsState.show_dismissed.to_string(),
                aria_controls="insights-dismissed-list",
                type="button",
            ),
            rx.cond(
                InsightsState.show_dismissed,
                rx.el.div(
                    rx.foreach(InsightsState.dismissed_cards, _dismissed_card),
                    class_name="insights-list",
                    id="insights-dismissed-list",
                ),
            ),
            class_name="insights-dismissed",
        ),
    )


@rx.page(
    route="/insights",
    title="Insights · Finance Analyzer",
    on_load=[InsightsState.check_auth, InsightsState.load_insights],
)
def insights() -> rx.Component:
    return rx.fragment(
        side_nav("insights"),
        rx.el.main(
            rx.el.div(
                rx.el.h1("What we noticed", class_name="insights-headline"),
                rx.el.p(
                    "These are patterns in your data — not judgments. We share what we see, "
                    "you decide what to do.",
                    class_name="insights-subline",
                ),
                _summary(),
                class_name="insights-header",
                id="insights-header",
            ),
            rx.cond(
                InsightsState.loaded,
                rx.cond(
                    InsightsState.has_anything,
                    rx.fragment(_wins_band(), _watch_band()),
                    _empty_state(),
                ),
                _skeleton(),
            ),
            _dismissed_section(),
            _footer(),
            class_name="has-sidenav",
        ),
    )
