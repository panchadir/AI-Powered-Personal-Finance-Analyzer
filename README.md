# AI-Powered Personal Finance Analyzer

A local-first personal finance app that reads your Indian bank statements (PDF/CSV), categorises transactions with a Tier-1 rules engine and a Tier-2 Claude AI fallback, computes a Safe-to-Spend figure and a Confidence Score, surfaces proactive spending insights, and answers natural-language questions via an AI Copilot.

## Prerequisites

- Python 3.11 or later
- Docker and Docker Compose (for `make demo`)
- An Anthropic API key (optional — the app runs without it but the AI Copilot and Tier-2 categorisation will be unavailable)

## One-command setup

```bash
git clone https://github.com/panchadir/AI-Powered-Personal-Finance-Analyzer.git
cd AI-Powered-Personal-Finance-Analyzer
make demo
```

This will:
1. Copy `.env.example` to `.env` (if `.env` does not already exist) and print instructions for adding your `ANTHROPIC_API_KEY`
2. Build and start the app + Postgres database via Docker Compose
3. Seed the canonical demo user and dataset (`demo@example.com` / `demodemo1`)
4. Print the app URL once ready

Open [http://localhost:3000](http://localhost:3000) and log in with `demo@example.com` / `demodemo1`.

## Resetting demo data

To wipe the demo user's data and re-seed for a clean demo run:

```bash
make reset
```

## Running tests

Engine unit tests (fast, no Docker needed):

```bash
pytest services/engine/
```

Full test suite:

```bash
pytest
```

Individual test modules:

```bash
pytest tests/security/test_idor.py        # cross-user data isolation
pytest tests/seed/test_seed_demo.py       # demo seed script
pytest tests/ui/test_empty_states.py      # empty-state component tests
```

## Project structure

```
finance_app/        Reflex pages and state (UI layer)
services/           Pure Python business logic (no Reflex imports)
  engine/           Safe-to-Spend and Confidence Score engine
  ingestion/        PDF/CSV parsers and dispatch
  categorize/       Tier-1 rules engine and Teach Me
  narrate/          Briefing, insight narration, AI Copilot
  analytics/        Spending-by-category aggregation
tests/              pytest suite (mirrors services/ and finance_app/)
scripts/            Utility scripts (seed_demo.py)
data/               Demo data (demo-data.json, sample statements)
alembic/            Database migrations
assets/             CSS design system (wds.css)
```

## Architecture decisions

The full architecture decision log is at:

```
_bmad-output/planning-artifacts/architecture/
  architecture-AI-Powered-Personal-Finance-Analyzer-2026-07-08/ARCHITECTURE-SPINE.md
```

Key decisions documented there:

- **AD-1** — No arithmetic outside `services/engine/`
- **AD-2** — `services/` never imports `reflex` or `finance_app`
- **AD-4** — Every DB query carries an explicit `user_id` filter (IDOR boundary)
- **AD-8** — Money is always `Decimal`, never `float`
- **AD-9** — Confidence Score writes are always atomic with an explanation event
- **AD-12** — Typed `IngestionError` hierarchy; no raw exceptions surfaced to the UI

## Environment variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `ANTHROPIC_API_KEY` | No | — | Enables AI Copilot and Tier-2 categorisation |
| `DATABASE_URL` | Yes (Docker sets it) | See `.env.example` | PostgreSQL connection string |

Copy `.env.example` to `.env` and fill in your key before running `make demo`.
