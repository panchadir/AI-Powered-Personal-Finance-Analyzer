"""The only permitted currency and date display functions (AD-13).

  - ``formatINR(amount: float) -> str``  Indian number grouping, e.g. ``₹1,25,000``
  - ``formatDate(iso: str) -> str``      ISO date to ``"30 Jun 2026"``

Direct f-string formatting of currency/dates in components or State handlers is not
acceptable. The prototype's ``shared/format.js`` is the JS twin — keep output identical.
Implemented in Story 1.2. Intentionally empty in Story 1.1.
"""
