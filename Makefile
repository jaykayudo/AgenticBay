.PHONY: help up down build restart logs ps \
        backend-shell backend-logs backend-lint backend-format backend-test backend-migrate backend-migrate-create \
        web-shell web-logs web-lint web-format web-type-check \
        db-shell db-reset redis-cli \
        install install-backend install-web

COMPOSE = docker compose
BACKEND = $(COMPOSE) exec backend
WEB     = $(COMPOSE) exec web

# ── Help ──────────────────────────────────────────────────────────────────────

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-30s\033[0m %s\n", $$1, $$2}' | sort

# ── Docker Compose ────────────────────────────────────────────────────────────

up: ## Start all services
	$(COMPOSE) up -d

up-build: ## Build and start all services
	$(COMPOSE) up -d --build

down: ## Stop all services
	$(COMPOSE) down

down-v: ## Stop all services and remove volumes
	$(COMPOSE) down -v

build: ## Build all Docker images
	$(COMPOSE) build

restart: ## Restart all services
	$(COMPOSE) restart

logs: ## Tail logs for all services
	$(COMPOSE) logs -f

ps: ## Show running containers
	$(COMPOSE) ps

# ── Backend ───────────────────────────────────────────────────────────────────

backend-shell: ## Open a shell in the backend container
	$(BACKEND) bash

backend-logs: ## Tail backend logs
	$(COMPOSE) logs -f backend

backend-lint: ## Run ruff lint on backend
	$(BACKEND) uv run ruff check .

backend-lint-fix: ## Run ruff lint with auto-fix on backend
	$(BACKEND) uv run ruff check --fix .

backend-format: ## Format backend code with ruff
	$(BACKEND) uv run ruff format .

backend-format-check: ## Check backend formatting without applying
	$(BACKEND) uv run ruff format --check .

backend-typecheck: ## Run mypy type checking on backend
	$(BACKEND) uv run mypy app

backend-test: ## Run backend tests
	$(BACKEND) uv run pytest -v

backend-test-cov: ## Run backend tests with coverage report
	$(BACKEND) uv run pytest --cov=app --cov-report=term-missing -v

backend-migrate: ## Run pending Alembic migrations
	$(BACKEND) uv run alembic upgrade head

backend-migrate-down: ## Rollback last Alembic migration
	$(BACKEND) uv run alembic downgrade -1

backend-migrate-create: ## Create a new Alembic migration (use: make backend-migrate-create MSG="your message")
	$(BACKEND) uv run alembic revision --autogenerate -m "$(MSG)"

backend-migrate-history: ## Show Alembic migration history
	$(BACKEND) uv run alembic history --verbose

backend-migrate-current: ## Show current Alembic revision
	$(BACKEND) uv run alembic current

# ── Web ───────────────────────────────────────────────────────────────────────

web-shell: ## Open a shell in the web container
	$(WEB) sh

web-logs: ## Tail web logs
	$(COMPOSE) logs -f web

web-lint: ## Run ESLint on web
	$(WEB) npm run lint

web-lint-fix: ## Run ESLint with auto-fix on web
	$(WEB) npm run lint:fix

web-format: ## Format web code with Prettier
	$(WEB) npm run format

web-format-check: ## Check web formatting without applying
	$(WEB) npm run format:check

web-type-check: ## Run TypeScript type check on web
	$(WEB) npm run type-check

# ── Database ──────────────────────────────────────────────────────────────────

db-shell: ## Open a psql shell in the postgres container
	$(COMPOSE) exec postgres psql -U postgres -d agentic_bay

db-reset: ## Drop and recreate the database (destructive!)
	$(COMPOSE) exec postgres psql -U postgres -c "DROP DATABASE IF EXISTS agentic_bay;"
	$(COMPOSE) exec postgres psql -U postgres -c "CREATE DATABASE agentic_bay;"
	$(MAKE) backend-migrate

redis-cli: ## Open a redis-cli shell
	$(COMPOSE) exec redis redis-cli

# ── Local Dev (no Docker) ────────────────────────────────────────────────────

install-backend: ## Install backend dependencies locally with uv
	cd backend && uv pip install --system -e ".[dev]"

install-web: ## Install web dependencies locally
	cd web && npm install

install: install-backend install-web ## Install all dependencies locally

lint: backend-lint web-lint ## Run lint on both backend and web

format: backend-format web-format ## Format both backend and web

# ── CI shortcuts ──────────────────────────────────────────────────────────────

ci-backend: ## Run full backend CI checks (lint, format, typecheck, test) locally
	cd backend && uv run ruff check . && uv run ruff format --check . && uv run mypy app && uv run pytest -v

ci-web: ## Run full web CI checks (lint, format, typecheck) locally
	cd web && npm run lint && npm run format:check && npm run type-check
