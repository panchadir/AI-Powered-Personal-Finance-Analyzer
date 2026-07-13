"""Build-time smoke coverage for every page + shared component.

Each ``@rx.page`` function and its private helpers construct a Reflex component tree. Calling
the top-level page function exercises those helpers — and, crucially, ``rx.foreach`` invokes
its render function once at build time to construct the child template, so the per-item render
functions (``_insight_card``, ``_commitment_row``, ``_message_bubble``, …) are covered too.
Building a page also catches Reflex API misuse that a pure structural test would miss.
"""
from __future__ import annotations

import pytest
import reflex as rx

from finance_app.components.nav import side_nav
from finance_app.components.placeholder import coming_soon
from finance_app.components.skeleton import (
    card_skeleton,
    chart_skeleton,
    dashboard_skeleton,
    sts_skeleton,
    txn_skeleton,
)
from finance_app.pages.auth import auth
from finance_app.pages.commitments import commitments
from finance_app.pages.copilot import copilot
from finance_app.pages.dashboard import dashboard
from finance_app.pages.insights import insights
from finance_app.pages.register import register
from finance_app.pages.transactions import transactions
from finance_app.pages.upload import upload


@pytest.mark.parametrize(
    "page_fn",
    [auth, register, upload, dashboard, transactions, insights, commitments, copilot],
    ids=lambda f: f.__name__,
)
def test_page_builds_without_error(page_fn):
    assert isinstance(page_fn(), rx.Component)


@pytest.mark.parametrize("active", ["dashboard", "transactions", "insights", "copilot"])
def test_side_nav_builds_for_every_tab(active):
    assert isinstance(side_nav(active), rx.Component)


@pytest.mark.parametrize(
    "skeleton_fn",
    [sts_skeleton, dashboard_skeleton, chart_skeleton, txn_skeleton],
    ids=lambda f: f.__name__,
)
def test_skeletons_build(skeleton_fn):
    assert isinstance(skeleton_fn(), rx.Component)


def test_card_skeleton_variants():
    assert isinstance(card_skeleton(lines=2, with_button=True), rx.Component)
    assert isinstance(card_skeleton(lines=5, with_button=False), rx.Component)


def test_placeholder_coming_soon_builds():
    assert isinstance(coming_soon("Insights"), rx.Component)


def test_app_entrypoint_imports():
    # Constructing the rx.App (module import side effect) must not raise.
    import finance_app.finance_app as app_module

    assert app_module.app is not None
