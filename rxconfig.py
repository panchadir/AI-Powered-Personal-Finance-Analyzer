import reflex as rx

config = rx.Config(
    app_name="finance_app",
    plugins=[
        rx.plugins.SitemapPlugin(),
        rx.plugins.TailwindV4Plugin(),
        # Explicit Radix Themes enablement (implicit enablement deprecated in 0.9.0,
        # removed in 1.0). The skeleton pages use Radix components (rx.heading, etc.).
        rx.plugins.RadixThemesPlugin(),
    ],
)
