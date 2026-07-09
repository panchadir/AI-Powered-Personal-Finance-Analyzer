"""Finance Analyzer — Reflex app entrypoint.

Importing ``finance_app.pages`` registers all six ``@rx.page`` routes (auth, upload,
transactions, dashboard, insights, copilot) before the app is constructed. Pages
orchestrate only; business logic lives in ``services/`` (AD-2).
"""

import reflex as rx

from finance_app import pages  # noqa: F401  (import registers all @rx.page routes)

app = rx.App()
