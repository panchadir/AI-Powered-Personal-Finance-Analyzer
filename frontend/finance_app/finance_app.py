"""Finance Analyzer — Reflex app entrypoint.

Importing ``finance_app.pages`` registers every ``@rx.page`` route (auth, upload,
transactions, dashboard, commitments, insights, copilot) before the app is constructed.
Pages orchestrate only; business logic lives in ``services/`` (AD-2).

UI baseline: the approved **WDS prototype** is the source of truth for all screens
(``prototypes/01-priyas-first-honest-morning-Prototype``). Its self-contained design
system is reused verbatim as ``assets/wds.css`` — pages render the prototype markup with
the same class names, so the app inherits the calm-teal brand, Inter type, pill buttons
and elevated cards rather than the default Radix look. ``has_background=False`` lets the
prototype's ``body { background: var(--bg) }`` show through the Radix Themes container.
"""

import reflex as rx

from finance_app import models  # noqa: F401  (import registers DB tables for migrations — Story 1.2)
from finance_app import pages  # noqa: F401  (import registers all @rx.page routes)

app = rx.App(
    # Reuse the WDS prototype's own stylesheet (design tokens + component classes) verbatim.
    # The WDS theme (teal accent, transparent bg) is configured on RadixThemesPlugin in
    # rxconfig.py — App(theme=...) is deprecated in Reflex 0.9.0.
    stylesheets=["/wds.css"],
)
