"""Named detector thresholds (Story 7.1, AC #8). No magic numbers inside detector logic.

Each constant is an honest, defensible default for the single-user MVP; tune here, never
inline. Cited to FR-8.1 / the PRD journey. Money thresholds are ``Decimal`` (AD-8).
"""
from __future__ import annotations

from decimal import Decimal

# --- Post-payday spike (FR-8.1) --------------------------------------------------
POST_PAYDAY_WINDOW_DAYS = 3  # "spending jumps in the 3 days after salary" (PRD journey §6)
POST_PAYDAY_SPIKE_MIN_PCT = Decimal("40")  # post-window daily rate ≥ 40% over baseline

# --- Death by small purchases (FR-8.1) -------------------------------------------
SMALL_PURCHASE_MAX_AMOUNT = Decimal("500")  # a "small" debit is ≤ ₹500
SMALL_PURCHASE_MIN_COUNT = 8  # this many small debits ...
SMALL_PURCHASE_MIN_TOTAL = Decimal("2000")  # ... summing to at least this much

# --- Zombie subscriptions (FR-8.1) -----------------------------------------------
SUBSCRIPTION_AMOUNT_TOLERANCE_PCT = Decimal("10")  # ±10% amount counts as the "same" charge
SUBSCRIPTION_MIN_OCCURRENCES = 2  # seen at least twice to call it recurring
SUBSCRIPTION_MIN_GAP_DAYS = 20  # ~monthly cadence lower bound
SUBSCRIPTION_MAX_GAP_DAYS = 40  # ~monthly cadence upper bound

# --- Weekend vs weekday pace (FR-8.1) --------------------------------------------
WEEKEND_PACE_MIN_RATIO = Decimal("1.5")  # weekend daily rate ≥ 1.5× weekday rate
WEEKEND_PACE_MIN_WEEKEND_DAYS = 2  # need >=1 full weekend of data to be statistically honest

# --- Upcoming commitment collision (FR-8.1) --------------------------------------
COLLISION_LOOKAHEAD_DAYS = 7  # only commitments due within a week of as_of
COLLISION_MIN_BALANCE = Decimal("0")  # projected running balance below this → collision

# --- Shared ----------------------------------------------------------------------
MAX_EVIDENCE_POINTS = 3  # FR-8.2: cite 2–3 exact data points per insight
MIN_DATA_MONTHS_FOOTNOTE = 3  # FR-8.5: below this, Story 7.3 shows the footnote

# --- Dismiss / resurface lifecycle (Story 7.3) ------------------------------------
# A dismissed pattern only resurfaces once its per-pattern headline metric moves by at
# least this percentage (Story 7.3's caller compares the new candidate's metric against
# the last dismissed row's stored value; never un-dismisses the old row -- always inserts
# a new one).
MATERIAL_CHANGE_THRESHOLD_PCT = Decimal("15")
