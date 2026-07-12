.PHONY: demo reset test test-all help

# ── One-command demo setup ─────────────────────────────────────────────────────
demo: ## Build, start, and seed the demo (first-time or after a clean clone)
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo ""; \
		echo "  Created .env from .env.example."; \
		echo "  If you have an Anthropic API key, add it now:"; \
		echo "    ANTHROPIC_API_KEY=sk-ant-..."; \
		echo "  (The app runs without it but the AI Copilot will be unavailable.)"; \
		echo ""; \
	fi
	docker compose up -d --build
	@echo "Waiting for the app container and database to be ready..."
	@elapsed=0; \
	until docker compose exec app python -c "from finance_app.models import Transaction" 2>/dev/null; do \
		sleep 2; elapsed=$$((elapsed+2)); \
		if [ $$elapsed -ge 120 ]; then echo "ERROR: container did not become ready after 120s." && exit 1; fi; \
	done
	docker compose exec app python scripts/seed_demo.py
	@echo ""
	@echo "  Demo ready at http://localhost:3000"
	@echo "  Login: demo@example.com / demodemo1"
	@echo ""

# ── Reset demo data ────────────────────────────────────────────────────────────
reset: ## Wipe the demo user's data and re-seed for a clean demo run
	docker compose exec app python scripts/seed_demo.py --reset
	@echo "Demo data reset. Login: demo@example.com / demodemo1"

# ── Tests ──────────────────────────────────────────────────────────────────────
test: ## Run the engine unit tests (fast, no Docker needed)
	pytest services/engine/

test-all: ## Run the full test suite
	pytest

# ── Help ───────────────────────────────────────────────────────────────────────
help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*##' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*##"}; {printf "  %-12s %s\n", $$1, $$2}'
