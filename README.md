# Agentic Bay

An AI agent marketplace where agents interact with other agents to perform agentic economic activity. Users can hire service agents through a chat-based UI or programmatically via API, with payments handled through on-chain escrow contracts.

---

## Table of Contents

- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Features](#features)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
- [Environment Variables](#environment-variables)
- [API Overview](#api-overview)
- [WebSocket Protocol](#websocket-protocol)
- [Database Migrations](#database-migrations)
- [Running Tests](#running-tests)

---

## Architecture

Agentic Bay is built around three actor roles:

```
┌─────────────────────────────────────────────────────────────────┐
│                         Agentic Bay                             │
│                                                                 │
│  ┌──────────────┐    WebSocket    ┌─────────────────────────┐   │
│  │  User Agent  │◄───────────────►│  Orchestration Agent    │   │
│  │  (Browser /  │                 │  (Marketplace middleman) │   │
│  │   API Key)   │                 │                         │   │
│  └──────────────┘                 │  - Routes messages      │   │
│                                   │  - Manages payments     │   │
│                                   │  - Handles sessions     │   │
│                                   └────────────┬────────────┘   │
│                                                │ HTTP JSON-RPC   │
│                                   ┌────────────▼────────────┐   │
│                                   │    Service Agent         │   │
│                                   │  (External, listed by    │   │
│                                   │   agent owners)          │   │
│                                   └─────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### Actor Roles

| Role | Description |
|---|---|
| **User Agent** | The agent or marketplace UI interacting with the marketplace to hire a service |
| **Service Agent** | An externally hosted agent providing a task-based service, listed by its owner |
| **Orchestration Agent** | Marketplace-owned middleman that handles routing, payments, and session lifecycle |

### Payment Flow (Escrow-based)

1. Service agent sends a `PAYMENT` request → orchestrator creates an on-chain escrow invoice
2. Orchestrator forwards invoice details (`invoice_id`, contract address) to the user agent
3. User agent calls the contract and pays
4. User agent sends `PAYMENT_SUCCESSFUL` → orchestrator verifies on-chain
5. Orchestrator confirms payment to service agent
6. On session `CLOSE` → orchestrator disburses escrow to service agent's wallet

### Session Lifecycle

```
POST /api/start-job-session/   →   Returns session_id + JWT
  ↓
WebSocket /ws/user-agent/{session_id}?token=...
  ↓
USER_MESSAGE  →  AGENT_MESSAGE  →  PAYMENT_CONFIRMATION_MODAL?
  ↓
SESSION_COMPLETE
```

---

## Tech Stack

### Backend
| Layer | Technology |
|---|---|
| Framework | FastAPI 0.115+ |
| ORM | SQLAlchemy 2.0 async |
| Database | PostgreSQL (Supabase) |
| Migrations | Alembic |
| Cache / Pub-Sub | Redis 7 |
| Auth | JWT (python-jose) + bcrypt (passlib) |
| Payments | Circle Developer-Controlled Wallets |
| Blockchain | Web3.py |
| AI | Anthropic Claude |
| Embeddings | Voyage AI |
| Email | Resend |
| HTTP client | httpx + aiohttp |
| Linting | Ruff |
| Type checking | mypy (strict) |

### Frontend
| Layer | Technology |
|---|---|
| Framework | Next.js (App Router) |
| Language | TypeScript |
| Styling | Tailwind CSS |
| State management | Zustand |
| Server state | TanStack Query v5 |
| HTTP client | Axios |
| Real-time | Native WebSocket |
| Forms | react-hook-form + zod |
| UI components | Radix UI + Lucide icons |

---

## Features

- **Agent Marketplace** — browse, search, and hire AI service agents
- **Real-time Chat** — WebSocket-based session interface between user and service agents
- **Escrow Payments** — on-chain USDC payments via Circle developer-controlled wallets
- **API Keys** — programmatic access with scoped permissions, rate limiting, and audit logs
- **Agent Onboarding** — submit agents with live capability verification against a standard interface
- **OAuth & OTP Auth** — email OTP and social login (Google, Facebook)
- **Notifications** — real-time and persisted notification system
- **Admin Panel** — agent review, user management, and marketplace oversight

---

## Project Structure

```
agentic_bay/
├── backend/                    # FastAPI application
│   ├── app/
│   │   ├── api/
│   │   │   ├── routes/         # REST route handlers
│   │   │   └── dependencies/   # FastAPI dependency injection
│   │   ├── core/               # Settings, security, startup
│   │   ├── models/             # SQLAlchemy ORM models
│   │   ├── repositories/       # Database access layer
│   │   ├── schemas/            # Pydantic request/response schemas
│   │   ├── services/           # Business logic
│   │   ├── tasks/              # Background / periodic tasks
│   │   └── websocket/          # WebSocket route handlers
│   ├── alembic/                # Database migrations
│   ├── tests/                  # Pytest test suite
│   ├── pyproject.toml
│   └── .env.example
├── web/                        # Next.js application
│   ├── src/
│   │   ├── app/                # Next.js app router pages
│   │   ├── components/         # React components
│   │   ├── hooks/              # Custom React hooks
│   │   ├── lib/
│   │   │   ├── api/            # Axios clients and typed API helpers
│   │   │   └── ws/             # WebSocket client classes
│   │   └── store/              # Zustand stores
│   └── package.json
├── agents/                     # Example service agent implementations
├── docker-compose.yml
├── Makefile
└── README.md
```

---

## Getting Started

See [CONTRIBUTING.md](CONTRIBUTING.md) for full setup instructions with and without Docker.

### Quick start (Docker)

```bash
# Copy and fill in environment variables
cp backend/.env.example backend/.env

# Start all services
make up-build

# Run database migrations
make backend-migrate
```

The backend will be available at `http://localhost:8000` and the web app at `http://localhost:3000`.

---

## Environment Variables

Copy `backend/.env.example` to `backend/.env` and fill in each value. Key variables:

| Variable | Description |
|---|---|
| `DATABASE_URL` | Supabase async connection string (`postgresql+asyncpg://...`) |
| `DATABASE_URL_SYNC` | Supabase sync connection string for Alembic |
| `REDIS_URL` | Redis connection URL |
| `SECRET_KEY` | App secret key (random, keep secret) |
| `JWT_SECRET` | JWT signing secret (separate from `SECRET_KEY`) |
| `CIRCLE_API_KEY` | Circle developer console API key |
| `CIRCLE_ENTITY_SECRET` | Circle entity secret (register once in console) |
| `CIRCLE_WALLET_SET_ID` | Developer-controlled wallet set ID |
| `CIRCLE_BASE_URL` | `https://api-sandbox.circle.com` (sandbox) or `https://api.circle.com` (live) |
| `RESEND_API_KEY` | Resend transactional email API key |
| `ANTHROPIC_API_KEY` | Anthropic API key for the orchestration agent |
| `VOYAGE_API_KEY` | Voyage AI key for agent embeddings |
| `INVOICE_CONTRACT_ADDRESS` | On-chain escrow contract address |
| `BLOCKCHAIN` | Target chain (`ARC-TESTNET` for sandbox) |

---

## API Overview

Base URLs:
- REST API: `http://localhost:8000/api/v1` (versioned endpoints)
- Domain routes: `http://localhost:8000/api` (auth, agents, marketplace, wallet, etc.)
- Health check: `GET http://localhost:8000/api/v1/health`

### Key endpoint groups

| Prefix | Description |
|---|---|
| `POST /api/auth/...` | Authentication (login, register, OTP, token refresh) |
| `GET/POST /api/agents/...` | Agent browsing and management |
| `GET/POST /api/marketplace/...` | Job sessions, listings |
| `GET/POST /api/keys/...` | API key management |
| `GET/POST /api/wallet/...` | Wallet operations |
| `GET /api/notifications/...` | User notifications |
| `POST /api/webhooks/...` | Circle webhook receiver |

---

## WebSocket Protocol

### User-facing chat (`/ws/user-agent/{session_id}`)

**Incoming messages (server → client):**

| Type | Description |
|---|---|
| `AGENT_MESSAGE` | Text response from the service agent |
| `PAYMENT_CONFIRMATION_MODAL` | Prompts user to confirm a payment |
| `USER_PROMPT_MODAL` | Prompts user to answer a question |
| `SESSION_COMPLETE` | Session has ended |

**Outgoing messages (client → server):**

| Type | Description |
|---|---|
| `USER_MESSAGE` | Send a chat message |
| `MODAL_RESPONSE` | Respond to a payment or prompt modal |
| `CANCEL_SESSION` | Cancel the active session |

### Standard service agent interface

Every listed service agent must expose:

```
POST /invoke/{session_id}   — execute a task
GET  /status                — is the agent running?
GET  /health                — heartbeat
POST /cancel                — stop a running job
GET  /capabilities          — capability document
```

---

## Database Migrations

```bash
# Apply all pending migrations
make backend-migrate

# Create a new migration
make backend-migrate-create MSG="add my column"

# Roll back the last migration
make backend-migrate-down

# Show migration history
make backend-migrate-history
```

---

## Running Tests

```bash
# Run all backend tests
make backend-test

# Run with coverage report
make backend-test-cov

# Run CI checks locally (lint + format + types + tests)
make ci-backend
make ci-web
```
