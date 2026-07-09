"""Route pages, one file per route.

Importing this package imports every page module, which registers each ``@rx.page``
with Reflex before ``rx.App()`` is constructed in ``finance_app.finance_app``.
"""

from . import auth, upload, transactions, dashboard, insights, copilot

__all__ = ["auth", "upload", "transactions", "dashboard", "insights", "copilot"]
