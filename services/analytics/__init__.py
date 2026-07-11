"""Display-only spending aggregation for the Dashboard charts (Story 5.4).

Pure, deterministic, framework-agnostic (AD-2): nothing here imports ``reflex`` or
``finance_app``. Money is :class:`~decimal.Decimal` (AD-8). These aggregations exist so the
Dashboard's ``rx.State`` carries no arithmetic (AD-1 / NFR-3) — the state layer only turns
these numbers into a Plotly figure and formats them with ``formatINR`` (NFR-7).
"""
from services.analytics.spending import (
    CategorySlice,
    MonthPoint,
    monthly_spend,
    spending_by_category,
)

__all__ = [
    "CategorySlice",
    "MonthPoint",
    "spending_by_category",
    "monthly_spend",
]
