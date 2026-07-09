import os

import reflex as rx
from dotenv import load_dotenv

load_dotenv()

config = rx.Config(
    app_name="finance_app",
    db_url=os.environ["DATABASE_URL"],
    # Bind backend to all interfaces so it's reachable inside Docker.
    backend_host="0.0.0.0",
    plugins=[
        rx.plugins.SitemapPlugin(),
        rx.plugins.TailwindV4Plugin(),
        # Explicit Radix Themes enablement (implicit enablement deprecated in 0.9.0,
        # removed in 1.0). The skeleton pages use Radix components (rx.heading, etc.).
        rx.plugins.RadixThemesPlugin(),
    ],
)
