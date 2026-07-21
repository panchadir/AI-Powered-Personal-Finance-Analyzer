import os

import reflex as rx
from dotenv import load_dotenv

load_dotenv()

config = rx.Config(
    app_name="finance_app",
    # Postgres is the Phase-1 store. Default to the local Postgres DSN from
    # .env.example so a fresh checkout runs `pytest`/`reflex run` out-of-the-box
    # without a committed `.env`, instead of crashing on a missing DATABASE_URL.
    # `or` (not just get's default) also covers a present-but-empty DATABASE_URL.
    # Docker/other deployments always set DATABASE_URL, so this fallback is dev-only.
    # Keep in sync with the identical fallback in alembic/env.py.
    db_url=os.environ.get("DATABASE_URL")
    or "postgresql+psycopg2://finance_user:finance_pass@localhost:5432/finance_db",
    # Bind backend to all interfaces so it's reachable inside Docker.
    backend_host="0.0.0.0",
    plugins=[
        rx.plugins.SitemapPlugin(),
        rx.plugins.TailwindV4Plugin(),
        # Explicit Radix Themes enablement (implicit enablement deprecated in 0.9.0,
        # removed in 1.0). The skeleton pages use Radix components (rx.heading, etc.).
        # Theme configured here (App(theme=...) is deprecated in 0.9.0): harmonize Radix
        # components with the WDS palette while wds.css owns the branded look. accent=teal
        # ≈ brand --primary #10796b; has_background=False lets wds.css's page bg show through.
        rx.plugins.RadixThemesPlugin(
            theme=rx.theme(
                appearance="light",
                accent_color="teal",
                gray_color="sage",
                radius="large",
                has_background=False,
            ),
        ),
    ],
)
