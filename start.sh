#!/usr/bin/env bash
# start.sh — Agentic Bay full-stack Docker startup script
#
# Usage:
#   ./start.sh              # start core services (postgres, redis, backend, web)
#   ./start.sh --with-agents  # also start the example service agents
#   ./start.sh --no-local-db  # skip local postgres (uses DATABASE_URL from .env)
set -euo pipefail

# ─── Colours ──────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No colour

info()    { echo -e "${BLUE}[INFO]${NC}  $*"; }
success() { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*" >&2; }
step()    { echo -e "\n${BOLD}==> $*${NC}"; }

# ─── Argument parsing ────────────────────────────────────────────────────────��
WITH_AGENTS=false
USE_LOCAL_DB=true

for arg in "$@"; do
  case $arg in
    --with-agents)  WITH_AGENTS=true  ;;
    --no-local-db)  USE_LOCAL_DB=false ;;
    --help|-h)
      echo "Usage: $0 [--with-agents] [--no-local-db]"
      echo "  --with-agents   Also start the example service agents (ports 5001–5003)"
      echo "  --no-local-db   Skip the local postgres container (use a remote database)"
      exit 0
      ;;
    *) error "Unknown argument: $arg"; exit 1 ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ─── 1. Pre-flight checks ─────────────────────────────────────────────────────
step "Pre-flight checks"

if ! command -v docker &>/dev/null; then
  error "Docker is not installed. Install Docker Desktop from https://www.docker.com/products/docker-desktop/"
  exit 1
fi

if ! docker info &>/dev/null; then
  error "Docker daemon is not running. Please start Docker Desktop and try again."
  exit 1
fi

if ! docker compose version &>/dev/null; then
  error "docker compose (v2) is required. Update Docker Desktop or install the compose plugin."
  exit 1
fi

success "Docker $(docker --version | awk '{print $3}' | tr -d ',')"

# ─── 2. Environment file setup ────────────────────────────────────────────────
step "Checking environment files"

# Root .env — docker-compose variable substitution
if [[ ! -f ".env" ]]; then
  warn "Root .env not found — creating with defaults"
  cat > .env <<'EOF'
BACKEND_URL=http://localhost:8000
BACKEND_WS_URL=ws://localhost:8000
DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/agentic_bay
DATABASE_URL_SYNC=postgresql+psycopg2://postgres:postgres@postgres:5432/agentic_bay
EOF
  success "Created .env"
else
  success ".env exists"
fi

# backend/.env — application config
if [[ ! -f "backend/.env" ]]; then
  warn "backend/.env not found — copying from backend/.env.example"
  cp backend/.env.example backend/.env

  # Replace placeholder DB URLs with docker-friendly values
  if [[ "$USE_LOCAL_DB" == "true" ]]; then
    sed -i.bak \
      -e 's|^DATABASE_URL=.*|DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/agentic_bay|' \
      -e 's|^DATABASE_URL_SYNC=.*|DATABASE_URL_SYNC=postgresql+psycopg2://postgres:postgres@postgres:5432/agentic_bay|' \
      -e 's|^REDIS_URL=.*|REDIS_URL=redis://redis:6379/0|' \
      backend/.env
    rm -f backend/.env.bak
  fi

  # Auto-generate SECRET_KEY and JWT_SECRET so the backend can start
  SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))" 2>/dev/null || openssl rand -hex 32)
  JWT_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))" 2>/dev/null || openssl rand -hex 32)
  sed -i.bak \
    -e "s|^SECRET_KEY=.*|SECRET_KEY=${SECRET_KEY}|" \
    -e "s|^JWT_SECRET=.*|JWT_SECRET=${JWT_SECRET}|" \
    backend/.env
  rm -f backend/.env.bak

  echo ""
  warn "backend/.env created from template. Fill in the following before starting:"
  warn "  CIRCLE_API_KEY, CIRCLE_ENTITY_SECRET, CIRCLE_WALLET_SET_ID"
  warn "  RESEND_API_KEY (optional — email features won't work without it)"
  warn "  ANTHROPIC_API_KEY, VOYAGE_API_KEY (required for orchestrator agent)"
  echo ""
  read -r -p "Continue anyway? The app will start but some features will be disabled. [y/N] " confirm
  [[ "${confirm,,}" == "y" ]] || exit 0
else
  success "backend/.env exists"
fi

# Service agent .env files (only required when starting with --with-agents)
if [[ "$WITH_AGENTS" == "true" ]]; then
  for agent in document-summarizer research web-scraper; do
    dir="examples/service-agents/$agent"
    if [[ ! -f "$dir/.env" ]]; then
      warn "$dir/.env not found — copying from .env.example (fill in API keys before using)"
      cp "$dir/.env.example" "$dir/.env"
    else
      success "$dir/.env exists"
    fi
  done
fi

# ─── 3. Build images ──────────────────────────────────────────────────────────
step "Building Docker images"

COMPOSE_PROFILES="local-db"
[[ "$WITH_AGENTS" == "true" ]] && COMPOSE_PROFILES="local-db,agents"
[[ "$USE_LOCAL_DB" == "false" ]] && COMPOSE_PROFILES=""
[[ "$USE_LOCAL_DB" == "false" && "$WITH_AGENTS" == "true" ]] && COMPOSE_PROFILES="agents"

if [[ -n "$COMPOSE_PROFILES" ]]; then
  PROFILE_FLAGS="--profile $(echo "$COMPOSE_PROFILES" | tr ',' ' --profile ')"
else
  PROFILE_FLAGS=""
fi

# shellcheck disable=SC2086
docker compose $PROFILE_FLAGS build --parallel
success "Images built"

# ─── 4. Start infrastructure ──────────────────────────────────────────────────
step "Starting infrastructure (Redis${USE_LOCAL_DB:+ + PostgreSQL})"

if [[ "$USE_LOCAL_DB" == "true" ]]; then
  docker compose --profile local-db up -d postgres redis
else
  docker compose up -d redis
fi

# ─── 5. Wait for Redis ────────────────────────────────────────────────────────
info "Waiting for Redis..."
until docker compose exec -T redis redis-cli ping 2>/dev/null | grep -q PONG; do
  printf '.'
  sleep 2
done
echo ""
success "Redis is ready"

# ─── 6. PostgreSQL: pgvector + agent_embeddings table ──────────────────────��──
if [[ "$USE_LOCAL_DB" == "true" ]]; then
  info "Waiting for PostgreSQL..."
  until docker compose --profile local-db exec -T postgres \
        pg_isready -U postgres -d agentic_bay &>/dev/null; do
    printf '.'
    sleep 2
  done
  echo ""
  success "PostgreSQL is ready"

  step "Installing pgvector extension"
  docker compose --profile local-db exec -T postgres \
    psql -U postgres -d agentic_bay -c "CREATE EXTENSION IF NOT EXISTS vector;" \
    && success "pgvector extension installed" \
    || { error "Failed to install pgvector extension"; exit 1; }

  step "Creating agent_embeddings table"
  docker compose --profile local-db exec -T postgres psql -U postgres -d agentic_bay << 'EOSQL'
CREATE TABLE IF NOT EXISTS agent_embeddings (
    agent_id   TEXT        PRIMARY KEY,
    name       TEXT        NOT NULL,
    description TEXT,
    category   TEXT,
    tags       TEXT[],
    rating     FLOAT       NOT NULL DEFAULT 0.0,
    pricing    JSONB       NOT NULL DEFAULT '{}',
    status     TEXT        NOT NULL DEFAULT 'ACTIVE',
    embedding  VECTOR(1024),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS agent_embeddings_embedding_idx
    ON agent_embeddings USING hnsw (embedding vector_cosine_ops);
EOSQL
  success "agent_embeddings table ready"
fi

# ─── 7. Start backend ─────────────────────────────────────────────────────────
step "Starting backend"
docker compose up -d backend
info "Waiting for backend to be healthy (this may take ~30 s on first run)..."
RETRIES=0
MAX_RETRIES=30
until curl -sf http://localhost:8000/api/v1/health &>/dev/null; do
  RETRIES=$((RETRIES + 1))
  if [[ $RETRIES -ge $MAX_RETRIES ]]; then
    error "Backend did not become healthy after ${MAX_RETRIES} attempts."
    error "Check logs with: docker compose logs backend"
    exit 1
  fi
  printf '.'
  sleep 3
done
echo ""
success "Backend is healthy"

# ─── 8. Run database migrations ───────────────────────────────────────────────
step "Running Alembic migrations"
docker compose exec -T backend uv run alembic upgrade head \
  && success "Migrations applied" \
  || { error "Migration failed — check logs with: docker compose logs backend"; exit 1; }

# ─── 9. Start web ─────────────────────────────────────────────────────────────
step "Starting web app"
docker compose up -d web
info "Waiting for web app..."
RETRIES=0
until curl -sf http://localhost:3000 &>/dev/null; do
  RETRIES=$((RETRIES + 1))
  if [[ $RETRIES -ge 30 ]]; then
    warn "Web app did not respond after 90 s — it may still be compiling."
    warn "Check logs with: docker compose logs web"
    break
  fi
  printf '.'
  sleep 3
done
echo ""

# ─── 10. Start example service agents (optional) ──────────────────────────────
if [[ "$WITH_AGENTS" == "true" ]]; then
  step "Starting example service agents"
  docker compose --profile agents up -d document-summarizer research-agent web-scraper
  success "Service agents started"
  warn "Fill in ORCHESTRATOR_API_KEY and other credentials in:"
  warn "  examples/service-agents/document-summarizer/.env"
  warn "  examples/service-agents/research/.env"
  warn "  examples/service-agents/web-scraper/.env"
fi

# ─── 11. Summary ──────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}${GREEN}╔══════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${GREEN}║          Agentic Bay is running!                 ║${NC}"
echo -e "${BOLD}${GREEN}╚══════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  ${BOLD}Web app:${NC}      http://localhost:3000"
echo -e "  ${BOLD}Backend API:${NC}  http://localhost:8000/api/v1"
echo -e "  ${BOLD}API docs:${NC}     http://localhost:8000/docs"
if [[ "$USE_LOCAL_DB" == "true" ]]; then
  echo -e "  ${BOLD}PostgreSQL:${NC}   localhost:5432  (user: postgres / pass: postgres)"
fi
echo -e "  ${BOLD}Redis:${NC}        localhost:6379"
if [[ "$WITH_AGENTS" == "true" ]]; then
  echo ""
  echo -e "  ${BOLD}Service agents:${NC}"
  echo -e "    document-summarizer  http://localhost:5001/health"
  echo -e "    research-agent       http://localhost:5002/health"
  echo -e "    web-scraper          http://localhost:5003/health"
fi
echo ""
echo -e "  ${BOLD}Useful commands:${NC}"
echo -e "    make logs             # tail all logs"
echo -e "    make backend-logs     # backend logs only"
echo -e "    docker compose down   # stop everything"
echo ""
