# Agentic Bay — Implementation Memory

This file is the canonical reference for any agent working on this codebase.
Read it fully before making changes.

---

## 1. What This Is

Agentic Bay is an AI agent marketplace. Users describe a task in natural language; the platform finds a matching service agent, negotiates payment, and delivers the result. There are three agent types:

| Agent | Role |
|---|---|
| **User Agent** | LLM-powered. Translates user natural language into typed orchestrator protocol. One instance per chat session. |
| **Orchestrator** | Routes messages between User Agent and Service Agent. Manages payment invoices, session state in Redis, and DB records. |
| **Service Agent** | A third-party microservice that performs actual work (summarization, scraping, etc.). Connects back to orchestrator via WebSocket dial-back. |

---

## 2. Repository Layout

```
agentic_bay/
├── backend/                     # FastAPI backend (Python, uv)
│   ├── app/
│   │   ├── agents/
│   │   │   ├── orchestrator/    # Orchestrator agent + session state
│   │   │   └── user_agent/      # Marketplace user agent (LLM loop)
│   │   ├── api/
│   │   │   ├── dependencies/    # FastAPI dependencies (auth, caller)
│   │   │   ├── routes/          # REST endpoints
│   │   │   └── deps.py          # get_session, get_cache, get_current_user_id
│   │   ├── auth/                # JWT helpers, OTP, session tokens
│   │   ├── core/                # config, database, redis, security
│   │   ├── models/              # SQLAlchemy ORM models
│   │   ├── repositories/        # DB access layer
│   │   ├── schemas/             # Pydantic request/response schemas
│   │   ├── services/            # Business logic
│   │   ├── tasks/               # Background tasks (invoice expiry, wallet sync)
│   │   └── websocket/           # WS endpoint handlers
│   ├── alembic/                 # DB migrations
│   └── tests/                   # pytest test suite
├── web/                         # Next.js frontend
├── examples/
│   └── service-agents/
│       └── document-summarizer/ # Reference service agent implementation
├── issue_descriptions.md        # Backlog of issues to implement
└── MEMORY.md                    # This file
```

---

## 3. Tooling Rules

- **Always use `uv run`** for all Python CLI commands. Never use `python -m` or bare executables.
  ```bash
  uv run pytest
  uv run alembic upgrade head
  uv run uvicorn app.main:app
  ```
- Working directory for backend commands: `backend/`
- All tests: `uv run pytest` — must stay green before and after every change.

---

## 4. Authentication — Two Keys, Two Flows

The system uses two separate JWT secrets for two separate purposes:

| Secret | Config key | Used for |
|---|---|---|
| `SECRET_KEY` | `settings.SECRET_KEY` | User access tokens (frontend login) |
| `JWT_SECRET` | `settings.JWT_SECRET` | Orchestrator session JWTs + chat session tokens |

### 4a. User Access Token (frontend auth)
- Issued at login. Payload: `{ sub, email, role, type: "access", sid, iat, exp }`.
- Decoded with `decode_access_token()` from `app/auth/jwt.py` (uses `SECRET_KEY`).
- Used by REST endpoints via `get_current_user` dependency in `app/api/dependencies/auth.py`.

### 4b. Chat Session Token (WS auth)
- Issued by `POST /api/sessions`. Short TTL: 5 minutes.
- Payload: `{ sub: user_id, session_id, type: "chat_session", iat, exp }`.
- Decoded with `decode_chat_session_token()` from `app/auth/session_token.py` (uses `JWT_SECRET`).
- Used by the WS endpoint `/ws/user-agent/{session_id}?token=<chat_session_token>`.

### 4c. Orchestrator Session JWT
- Issued internally when `OrchestratorWSClient` creates a job session.
- Payload: `{ session_id }`. Uses `JWT_SECRET`.
- Used to authenticate `/ws/user/{job_session_id}?token=<token>`.

### 4d. get_caller_user dependency (`app/api/dependencies/caller.py`)
Accepts **either** a Bearer JWT access token **or** an `x-api-key` header.
Used by `POST /api/sessions` so both our own frontend (JWT) and external user agent applications (API key) can start sessions.

---

## 5. Session Lifecycle

### Starting a chat session (correct flow)
```
1. Client → POST /api/sessions
   Auth: Bearer <access_token> OR x-api-key: <key>
   Response: { session_id, token, ws_url }

2. Client → WS /ws/user-agent/{session_id}?token=<token>
   (token = chat_session_token from step 1, NOT the access token)

3. Client sends: { "type": "USER_MESSAGE", "data": { "message": "..." } }
   First message → agent.start(); subsequent → agent.handle_user_message()
```

**The WS endpoint rejects connections if `session_id` is not found in DB or is CLOSED.**
Client-generated session IDs are never accepted.

### Inbound WS message types (frontend → server)
| Type | Handler |
|---|---|
| `USER_MESSAGE` | First: `agent.start()`, subsequent: `agent.handle_user_message()` |
| `MODAL_RESPONSE` | `agent.handle_user_response()` |
| `CANCEL_SESSION` | `agent.close()` |

### Outbound WS message types (server → frontend)
| Type | When |
|---|---|
| `AGENT_MESSAGE` | Agent status updates, responses, warnings |
| `PAYMENT_CONFIRMATION_MODAL` | User must approve a payment |
| `USER_PROMPT_MODAL` | Agent needs clarification |
| `SESSION_COMPLETE` | Session finished (success or failure) |

---

## 6. User Agent Internals (`app/agents/user_agent/`)

### LLM Loop (`agent.py → run_llm_turn`)
```
while True:
    response = await llm.call_with_tools(messages, tools, system_prompt)
    store assistant message in memory

    if stop_reason == "tool_use":
        for each tool_call:
            execute tool, store result in memory
            if close_session → closed = True
            if send_orchestrator_message / request_payment_confirmation / user_prompt
               → awaiting_external = True
        if closed or awaiting_external: return  ← EXIT (wait for external event)
        continue  ← give LLM the tool results

    else (end_turn):
        forward text to user via user_feedback
        break
```

**Turn-ending tools** — these break the loop because the agent must wait for an external response:
- `send_orchestrator_message` → waits for orchestrator reply
- `request_payment_confirmation` → waits for user modal response
- `user_prompt` → waits for user modal response
- `close_session` → session ends

### Tools (all in `app/agents/user_agent/tools/`)
| Tool | What it does |
|---|---|
| `send_orchestrator_message` | Sends typed message to orchestrator WS; updates agent state |
| `user_feedback` | Pushes `AGENT_MESSAGE` to frontend |
| `request_payment_confirmation` | Pushes `PAYMENT_CONFIRMATION_MODAL`; sets state=AWAITING_USER |
| `user_prompt` | Pushes `USER_PROMPT_MODAL`; sets state=AWAITING_USER |
| `api_request` | Makes authenticated HTTP requests to backend API |
| `close_session` | Sends `CLOSE` to orchestrator, `SESSION_COMPLETE` to frontend, calls `agent.close()` |

### Orchestrator Message Handlers (`message_handlers/`)
| Message type | Handler |
|---|---|
| `SEARCH_AGENT` | `SearchHandler` — injects search results as context, triggers LLM |
| `CONNECT` | `ConnectHandler` — injects capabilities as context, triggers LLM |
| `SERVICE_AGENT` | `ServiceHandler` — injects service response, triggers LLM |
| `PAYMENT` | `PaymentHandler` — loads auto-pay settings, injects context, triggers LLM |
| `PAYMENT_SUCCESSFUL` | `PaymentConfirmedHandler` — injects confirmation, triggers LLM |
| `CLOSE_APPEAL` | `CloseAppealHandler` — injects result, triggers LLM |
| `ERROR` | `ErrorHandler` — injects error context, triggers LLM |

### Memory (`memory.py`)
- Redis-backed. Key: `user_agent_memory:{session_id}`. TTL: 24 hours.
- `add_user_message`, `add_assistant_message`, `add_tool_result`, `add_system_context`.
- `get_messages_for_llm()` returns the full message list for the Anthropic API.

### Auto-Pay
- Settings on `User` model: `auto_pay_enabled`, `auto_pay_max_per_job`, `auto_pay_max_per_day`.
- `PaymentHandler` fetches user settings from DB and injects context into the LLM turn.
- If `auto_pay_enabled` and `amount <= auto_pay_max_per_job`: context tells LLM to send `PAYMENT_SUCCESSFUL` directly.
- Otherwise: context tells LLM to call `request_payment_confirmation`.

### LLM Model
- Model: `claude-sonnet-4-6` (used in both user agent and document summarizer).

---

## 7. Orchestrator WebSocket Protocol

### User Agent ↔ Orchestrator (WS `/ws/user/{session_id}?token={jwt}`)

**User Agent → Orchestrator:**
| Type | Key fields |
|---|---|
| `SEARCH_AGENT` | `data.message` (natural language) |
| `CONNECT_AGENT` | `data.agent_id` |
| `SERVICE_AGENT` | `data.command`, `data.arguments` |
| `PAYMENT_SUCCESSFUL` | `data.invoice_id` |
| `CLOSE` | — |

**Orchestrator → User Agent:**
| Type | Key fields |
|---|---|
| `SEARCH_AGENT` | `data.agents[]` (id, name, description, rating, pricing) |
| `CONNECT` | `data.agent_id`, `data.capabilities` (raw text) |
| `SERVICE_AGENT` | `data` or `message` (service result) |
| `PAYMENT` | `data.amount`, `data.description`, `data.payment_info.invoice_id/invoice_wallet/blockchain` |
| `PAYMENT_SUCCESSFUL` | `data.invoice_id` |
| `CLOSE_APPEAL` | `data.message`, `data.details` |
| `ERROR` | `data.error_type`, `data.message` |

### Orchestrator ↔ Service Agent
1. Orchestrator sends HTTP `POST /connect` to service agent with `{ session_id, token, orchestrator_ws_url, orchestrator_key }`.
2. Service agent dials back: `WS {orchestrator_ws_url}/ws/service/{session_id}?token={token}&key={orchestrator_key}`.
3. Orchestrator sends commands over WS. Service agent responds over the same WS.

---

## 8. Service Agent Contract

Every service agent must expose:
- `GET /capabilities` → `{ message: "<capability document text>" }`
- `POST /connect` → accepts `ServiceConnectRequest`, opens WS dial-back

WS messages service agent can send:
- `{ type: "PAYMENT", data: { amount, address?, description } }` — request payment
- `{ type: "JOB_DONE", data: { message, details } }` — signal completion
- `{ type: "PROGRESS", data: { progress?, message? } }` — optional progress update

**Payment-first gating pattern** (required): store pending work before sending PAYMENT; process on `payment_confirmed`. Never do work before payment clears.

Reference implementation: `examples/service-agents/document-summarizer/`

---

## 9. Database Models

All models extend `BaseModel` (`app/models/base.py`) which provides `id` (UUID, auto-generated), `created_at`, `updated_at`.

Key models:
| Model | Table | Notes |
|---|---|---|
| `User` | `users` | Has `auto_pay_enabled`, `auto_pay_max_per_job`, `auto_pay_max_per_day` |
| `Session` | `sessions` | One per user agent chat. `job_session_auth_token` = chat session JWT. `phase` mirrors `SessionPhase`. |
| `Agent` | `agents` | Registered service agents. Has `orchestrator_key` (unique per agent). |
| `ApiKey` | `api_keys` | User-created API keys for external access. Prefix + bcrypt hash. |
| `Invoice` | `invoices` | Payment invoice per job. Status lifecycle: PENDING → PAYMENT_CHECKING → PAID → DISBURSING → DISBURSED. |
| `Job` | `jobs` | One per service invocation within a session. |

### Migrations
- All migrations live in `backend/alembic/versions/`.
- Naming: `YYYYMMDD_NN_<description>.py`.
- Last migration: `20260425_04_add_auto_pay_fields_to_users.py`.
- Run: `uv run alembic upgrade head`

---

## 10. Repository Pattern

All DB access goes through repositories in `app/repositories/`. Each extends `BaseRepository[Model]`.

```python
# Use inside route/service:
repo = UserRepository(db)
user = await repo.get_by_id(user_id)
await repo.update(user_id, field=value)
```

Never write raw SQLAlchemy queries in routes or services — use or extend the repository.

---

## 11. Adding a New REST Endpoint

1. Create/edit a file in `app/api/routes/`.
2. Export the router from `app/api/routes/__init__.py`.
3. Register it in `app/main.py` with `app.include_router(router, prefix="/api")`.
4. Use `get_current_user` (JWT) or `get_caller_user` (JWT or API key) as the auth dependency.

---

## 12. Adding a New Alembic Migration

```bash
cd backend
uv run alembic revision --autogenerate -m "describe_change"
# Edit the generated file, then:
uv run alembic upgrade head
```

Name the file manually to follow the `YYYYMMDD_NN_` convention after autogenerate creates it.

---

## 13. Testing Conventions

- Test runner: `uv run pytest` from `backend/`.
- All tests must pass before and after every change.
- User agent tests use **fakes**, never real Redis or LLM:
  - `FakeMemory` — in-memory list
  - `FakeUserWS` / `FakeOrchestratorWS` — capture outbound messages
  - `ScriptedLLM` — returns a pre-programmed response sequence; safe `end_turn` fallback when exhausted
  - `build_agent()` in `tests/test_user_agent/conftest.py` wires all fakes together

- **Avoid `close_session` in the middle of a scripted sequence** — it calls `agent.close()` which clears memory; any memory assertions after that will fail. Use `_llm_response([_text_block(...)], stop_reason="end_turn")` for non-terminal turns.

---

## 14. Key Config Variables (`.env`)

| Variable | Purpose |
|---|---|
| `SECRET_KEY` | Signs user access tokens |
| `JWT_SECRET` | Signs orchestrator session JWTs + chat session tokens |
| `DATABASE_URL` | Async PostgreSQL URL (`postgresql+asyncpg://...`) |
| `DATABASE_URL_SYNC` | Sync PostgreSQL URL (`postgresql+psycopg2://...`) for Alembic |
| `REDIS_URL` | Redis connection string |
| `ORCHESTRATOR_WS_URL` | WS base URL for user agent → orchestrator connection |
| `CIRCLE_API_KEY` | Circle Wallets API key |
| `CIRCLE_ENTITY_SECRET` | 32-byte hex, registered once with Circle |
| `MARKETPLACE_FEE_PERCENT` | Platform fee (default 5.0%) |
| `BLOCKCHAIN` | Chain identifier (default `ARC-TESTNET`) |

---

## 15. Open Issues (see `issue_descriptions.md` for full details)

Issues are labelled B-# (backend) or O-# (orchestrator).

- **B-EMAIL**: Integrate Resend for transactional email delivery (`app/services/email_service.py`, `RESEND_API_KEY` env var).
- Other issues tracked in `issue_descriptions.md`.

---

## 16. Common Mistakes to Avoid

- **Do not use the user's access token for the WS connection.** The WS endpoint accepts only the short-lived `chat_session_token` from `POST /api/sessions`.
- **Do not let clients generate their own session IDs.** The WS rejects any `session_id` not found in DB.
- **Do not add LLM loop continuation after turn-ending tools.** After `send_orchestrator_message`, `request_payment_confirmation`, or `user_prompt`, the loop must `return` and wait for the external event.
- **Do not bypass the repository layer** with raw SQLAlchemy queries in routes or services.
- **Do not run `python` or `pytest` directly** — always prefix with `uv run`.
