# Contributing to Agentic Bay

Thank you for contributing. This guide covers how to run the project locally and the standards expected for pull requests.

---

## Table of Contents

- [Prerequisites](#prerequisites)
- [Running with Docker (recommended)](#running-with-docker-recommended)
- [Running without Docker](#running-without-docker)
- [Development Workflow](#development-workflow)
- [Pull Request Standards](#pull-request-standards)
- [Code Style](#code-style)

---

## Prerequisites

- **Docker Desktop** (if using Docker) — v24+
- **Python 3.11+** and [uv](https://docs.astral.sh/uv/) (if running backend locally)
- **Node.js 20+** and npm (if running web locally)
- A PostgreSQL database (Supabase or local)
- A Redis instance

---

## Running with Docker (recommended)

### 1. Configure environment

```bash
cp backend/.env.example backend/.env
# Edit backend/.env and fill in required values (database, Redis, API keys)
```

Minimum required variables for local development:

```env
DATABASE_URL=postgresql+asyncpg://...
DATABASE_URL_SYNC=postgresql+psycopg2://...
REDIS_URL=redis://redis:6379/0
SECRET_KEY=any-random-string
JWT_SECRET=another-random-string
```

### 2. Start services

```bash
# Build images and start all services
make up-build

# Or, to also spin up a local Postgres container (no Supabase needed):
make up-local-db    # starts Postgres only
make up-build       # then starts backend + web
```

### 3. Run migrations

```bash
make backend-migrate
```

### 4. Verify

- Backend: `http://localhost:8000/api/v1/health`
- Web app: `http://localhost:3000`

### Useful Docker commands

```bash
make logs              # tail all service logs
make backend-logs      # tail backend only
make web-logs          # tail web only
make backend-shell     # open a shell in the backend container
make web-shell         # open a shell in the web container
make down              # stop all services
make down-v            # stop and remove all volumes (destructive)
make restart           # restart all services
make ps                # show running containers
```

---

## Running without Docker

### Backend

```bash
cd backend

# Install dependencies (uv required)
uv sync --group dev

# Configure environment
cp .env.example .env
# Edit .env

# Run migrations
uv run alembic upgrade head

# Start the development server
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

> **Important:** All backend CLI commands must use `uv run`. Do not use `python -m` or bare executables.

### Web

```bash
cd web

# Install dependencies
npm install

# Configure environment
cp .env.local.example .env.local   # if the file exists, or create .env.local manually
# Set NEXT_PUBLIC_API_URL=http://localhost:8000
# Set NEXT_PUBLIC_WS_URL=ws://localhost:8000

# Start the development server
npm run dev
```

The web app will be available at `http://localhost:3000`.

---

## Development Workflow

### Backend

```bash
# Lint
make backend-lint          # check for issues
make backend-lint-fix      # auto-fix lint issues

# Format
make backend-format        # apply Ruff formatting
make backend-format-check  # check only (no writes)

# Type checking
make backend-typecheck     # run mypy (strict)

# Tests
make backend-test          # run test suite
make backend-test-cov      # run with coverage report

# Migrations
make backend-migrate                       # apply pending
make backend-migrate-create MSG="..."      # create new migration
make backend-migrate-down                  # roll back last
make backend-migrate-history               # view history
make backend-migrate-current               # current revision
```

Migration files follow the naming convention `YYYYMMDD_NN_description.py` and are stored in `backend/alembic/versions/`.

### Web

```bash
# Lint
make web-lint           # ESLint check
make web-lint-fix       # ESLint auto-fix

# Format
make web-format         # Prettier format
make web-format-check   # check only

# Type checking
make web-type-check     # TypeScript check
```

### Run full CI locally before pushing

```bash
make ci-backend   # lint + format check + mypy + pytest
make ci-web       # lint + format check + tsc
```

---

## Pull Request Standards

### Branch naming

```
feat/<short-description>       # new feature
fix/<short-description>        # bug fix
chore/<short-description>      # maintenance, deps, config
refactor/<short-description>   # code restructure without behavior change
docs/<short-description>       # documentation only
```

### Commit messages

Use the imperative mood and keep the subject line under 72 characters:

```
feat: add API key rotation endpoint
fix: correct expires_at timezone comparison in validate_key
chore: bump anthropic to 0.96.0
```

For non-trivial changes, add a body explaining the *why*:

```
fix: correct expires_at timezone comparison in validate_key

The stored datetime was naive; comparing against UTC-aware `now` raised
a TypeError. Replace `.replace(tzinfo=UTC)` with proper aware storage.
```

### PR checklist

Before opening a pull request, ensure:

- [ ] All CI checks pass: `make ci-backend && make ci-web`
- [ ] New backend code has corresponding tests in `backend/tests/`
- [ ] New database columns or tables have an Alembic migration
- [ ] No secrets, `.env` files, or credentials are committed
- [ ] The PR title follows the commit message convention above
- [ ] The PR description explains *what* changed and *why*
- [ ] Breaking changes to the WebSocket protocol or API response shape are called out explicitly

### PR description template

```markdown
## Summary
- What this PR does in 2–3 bullets

## Changes
- List of key files changed and why

## Testing
- How to verify the change manually
- Which tests cover it

## Notes (optional)
- Migrations needed? `make backend-migrate` after merge
- Any follow-up issues opened?
```

### Review guidelines

- Keep PRs focused — one logical change per PR
- Prefer small, incremental PRs over large all-in-one changes
- Respond to reviewer comments within two business days
- Resolve all conversations before merging
- Squash-merge feature branches; merge commits for release branches

---

## Code Style

### Backend (Python)

- Formatter: **Ruff** (`line-length = 100`)
- Linter: **Ruff** with `E, F, I, N, W, UP` rule sets
- Type checker: **mypy** (strict mode)
- Python version target: 3.11+
- Use `async`/`await` throughout — no synchronous database or network calls in route handlers
- All CLI commands use `uv run`

### Frontend (TypeScript)

- Formatter: **Prettier**
- Linter: **ESLint**
- Type checker: **tsc** (strict)
- No `any` types — use proper type assertions or generics
- Prefer named exports over default exports for components and hooks
- Keep React hooks in `src/hooks/`, API helpers in `src/lib/api/`, WebSocket clients in `src/lib/ws/`
