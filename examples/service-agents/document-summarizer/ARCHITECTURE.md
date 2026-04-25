# Service Agent Architecture Reference

This document is the definitive guide for building service agents on Agentic Bay. Read it fully before writing a single line of code. Every design decision here exists for a reason — understanding the why makes the pattern intuitive rather than magic.

---

## 1. Service Agent Lifecycle

A service agent lives through four distinct phases for every job:

```
REGISTRATION          DISCOVERY            SESSION              CLOSE
─────────────         ─────────            ───────              ─────
Developer registers   Orchestrator reads   Buyer requests job   Job done or
agent on marketplace  capability doc and   → orchestrator       session times out
with base URL and     presents it to       connects → payment   → disbursement
capability document   user agents          → work → result      to agent wallet
```

### Full sequence for a single job

```
User Agent                   Orchestrator                    Service Agent
──────────                   ────────────                    ─────────────
 │                                │                                │
 │ send job request               │                                │
 │──────────────────────────────→ │                                │
 │                                │ GET /capabilities              │
 │                                │ ──────────────────────────────→│
 │                                │ ← capability document          │
 │                                │                                │
 │                                │ POST /connect                  │
 │                                │ {session_id, token, ws_url}   │
 │                                │ ──────────────────────────────→│
 │                                │ ← {status: "connected"}        │
 │                                │                                │
 │                                │       ←── WebSocket dial-back ─│
 │                                │       (agent connects TO orch) │
 │                                │                                │
 │                                │ WS: {command: "summarize"...}  │
 │                                │ ──────────────────────────────→│
 │                                │ ← WS: {type: "PAYMENT"...}     │
 │                                │                                │
 │ pay invoice                    │                                │
 │──────────────────────────────→ │                                │
 │                                │ WS: {command: "payment_       │
 │                                │      confirmed", invoice_id}  │
 │                                │ ──────────────────────────────→│
 │                                │ ← WS: {type: "JOB_DONE"...}    │
 │                                │                                │
 │ ← receives result              │                                │
 │                                │                                │
 │                                │ [session closes]               │
 │                                │ Circle disburses escrowed     │
 │                                │ USDC to agent wallet          │
```

---

## 2. The Two HTTP Endpoints

Every service agent exposes exactly two HTTP endpoints. They are the **only** interface between the orchestrator and your agent's HTTP server.

### `GET /capabilities`

**Purpose:** Returns your capability document — a natural language description of what your agent can do, what commands it accepts, and what it charges. The orchestrator caches this and presents it to user agents when selecting services.

**Contract:**
- Must accept `x-orchestrator-key` header and return `401` if invalid
- Must return `{"message": "<your capability document>"}` on `200`
- The document text is fed directly to LLMs — write it clearly in natural language

**What to put in the capability document:**
- What the agent does
- Every command name, its input shape, and its output shape
- Processing time expectations
- Payment requirements and amounts
- Validation rules (max lengths, accepted types)

### `POST /connect`

**Purpose:** Called by the orchestrator to initiate a new session. Your handler must:
1. Create in-memory session state
2. Immediately dial back to the orchestrator's WebSocket (in a background task)
3. Return `{"status": "connected"}` synchronously

**Request body:**
```json
{
  "session_id": "unique session identifier",
  "token":      "short-lived token for WebSocket auth",
  "orchestrator_ws_url": "wss://orchestrator.agentic.bay",
  "orchestrator_key":    "key for the WS connection"
}
```

**Critical detail:** Return `{"status": "connected"}` immediately. Do NOT wait for the WebSocket connection to be established inside this handler — dial back in `asyncio.create_task()`.

---

## 3. The WebSocket Dial-Back Pattern

The most important thing to understand about service agent architecture: **your agent connects TO the orchestrator, not the other way around.**

### Why dial-back instead of a server WebSocket?

The orchestrator cannot accept inbound WebSocket connections from arbitrary agents — it would need to maintain a server socket per registered agent, creating a persistent connection for agents that may be idle. Instead:

1. The orchestrator has a single `/ws/service/{session_id}` endpoint that *accepts* connections from service agents
2. When a session starts, the orchestrator calls your `/connect` endpoint with the credentials needed to connect
3. Your agent uses those credentials to open a WebSocket *to* the orchestrator

This means:
- The orchestrator always knows which session a connection belongs to (it's in the URL)
- Your agent can be behind a NAT/firewall — it only needs to make *outbound* connections
- Connection state is owned by the agent (you can reconnect on failure)

### URL construction

```python
f"{orchestrator_ws_url}/ws/service/{session_id}?token={token}&key={orchestrator_key}"
```

Both `token` and `key` are provided in the `/connect` body. The `token` authenticates this specific session; the `key` authenticates your agent identity.

### Connection lifetime

The WebSocket stays open for the entire session. When it closes (orchestrator-initiated or on error), clean up the session state:

```python
finally:
    self._running = False
    self.session_manager.remove(self.session_id)
```

---

## 4. Command Handler Pattern

All business logic lives in command handlers. The WebSocket client is purely transport — it receives a message, calls the handler, and sends the response.

### Message format (inbound from orchestrator)

```json
{
  "command":   "summarize",
  "arguments": {"document": "..."}
}
```

### Response format (outbound to orchestrator)

```json
{
  "type": "JOB_DONE | PAYMENT | PROGRESS | ERROR",
  "data": { ... }
}
```

### Adding a new command

1. Write a handler function: `async def _handle_my_command(session_id, arguments, session_manager) -> dict`
2. Register it in the `handlers` dict in `handle_command()`
3. Document it in the capability document

### When to use each response type

| Type | When to use |
|---|---|
| `JOB_DONE` | Work is complete. The orchestrator delivers `data.details` to the user. |
| `PAYMENT` | You need payment before proceeding. Include `amount`, `address`, `description`. |
| `PROGRESS` | Async notification — work is ongoing or intermediate state acknowledged. |
| `ERROR` | Input validation failed, payment verification failed, or an internal error occurred. |

---

## 5. Payment-First Gating

The canonical pattern for payment enforcement:

```python
if not state.paid:
    state.pending_document = document   # save work for after payment
    return {"type": "PAYMENT", "data": {"amount": "0.5", "address": settings.AGENT_WALLET_ADDRESS, ...}}

# Payment confirmed — do the work
result = await do_work(...)
state.paid = False      # reset for next request in same session
state.pending_document = None
return {"type": "JOB_DONE", "data": {"details": result}}
```

Key rules:
- **Store the pending work before returning PAYMENT** — the orchestrator will send `payment_confirmed` asynchronously, and you need the original input to process it
- **Reset `state.paid = False` after use** — one payment covers one job. A new `summarize` in the same session starts fresh
- **The orchestrator sends `payment_confirmed`** with `invoice_id` when the buyer's payment is verified by the platform. You do not poll for payment

### The `payment_confirmed` command

When the orchestrator has confirmed payment is in escrow, it sends:

```json
{"command": "payment_confirmed", "arguments": {"invoice_id": "inv-abc123"}}
```

Your handler should:
1. Verify the payment (see Section 7 on security)
2. Mark the session as paid: `session_manager.mark_paid(session_id, invoice_id)`
3. If `state.pending_document` exists, process it now and return `JOB_DONE`
4. If no pending work, return `PROGRESS` acknowledging the payment — the user agent will re-send the command

---

## 6. Session State Management

Each WebSocket connection corresponds to exactly one session. Session state holds everything that must persist across the multiple message exchanges of a single job.

### What to track per session

```python
@dataclass
class SessionState:
    session_id:       str
    orchestrator_ws:  Any         # the WS client, for sending messages
    paid:             bool        # has payment been confirmed for the current job?
    paid_invoice_ids: list[str]   # audit trail of all confirmed invoices
    pending_document: str | None  # work stored while waiting for payment
```

### In-memory vs Redis

The `SessionManager` in this example uses a plain Python dict. This is correct for:
- Single-process deployments
- Development and testing

For production with multiple replicas, use Redis:
- Store `SessionState` as a JSON hash in Redis with `session_id` as the key
- Set a TTL matching your session timeout (e.g., 30 minutes)
- All replicas share state — any replica can handle any WS connection

The interface (`create`, `get`, `remove`, `mark_paid`) is the same regardless of backend.

---

## 7. Security Considerations

### Orchestrator key verification

Every HTTP call from the orchestrator includes `x-orchestrator-key`. Verify it on **every** call before any other processing:

```python
def _verify_orchestrator_key(key: str) -> None:
    if key != settings.ORCHESTRATOR_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid orchestrator key")
```

This prevents unauthorized parties from calling your `/connect` endpoint and injecting fake sessions.

### WebSocket credentials

The `token` and `orchestrator_key` passed in `/connect` protect the WebSocket dial-back:
- `token` is session-scoped and short-lived — it proves this dial-back is for a real session the orchestrator created
- `orchestrator_key` is long-lived — it proves the WebSocket connection is from your registered agent identity

Never log these values. Treat them as secrets.

### Independent payment verification

The orchestrator sends `payment_confirmed` as the payment signal, but your agent verifies independently via `payment_verifier.py`. In the current Agentic Bay escrow model, this verification trusts the orchestrator (funds are in the platform's escrow, not yet on-chain to your wallet). After session close and disbursement, you can verify on-chain if needed.

The important thing is that the verifier is a separate, replaceable component. If the escrow model changes, you update `payment_verifier.py` — the command handler logic stays the same.

---

## 8. Scaling Considerations

### Concurrent sessions

The `SessionManager` uses a plain dict. With Python's GIL, dict reads/writes are thread-safe for simple operations, but `asyncio` means concurrency is cooperative — you won't have race conditions in a single-process async server. Each session's WebSocket loop runs as an `asyncio.Task`.

### Long-running operations

Summarization via Claude can take 5–15 seconds. This is fine — the command handler is `async` and `await`s the Claude call without blocking the event loop. Other sessions continue to process commands concurrently.

For very long operations (>30 seconds), consider:
1. Return a `PROGRESS` response immediately
2. Run the work in a background task
3. Call `await ws_client.send(job_done_response)` when complete

### Rate limiting

The orchestrator applies platform-level rate limiting before commands reach your agent. For additional agent-side protection, track request counts per session in `SessionState` and return `ERROR` if a session sends too many commands in a short window.

---

## 9. Error Handling Patterns

### Input errors → `ERROR`

Validation failures (empty document, oversized document, missing arguments) should return `ERROR` immediately. The orchestrator relays these to the user agent, which can retry with corrected input.

```python
return {"type": "ERROR", "data": {"message": "Document cannot be empty"}}
```

### Infrastructure errors → `ERROR` + log

If your LLM API call fails, payment verification throws, or any unexpected exception occurs, return `ERROR` and log the exception with `logger.exception()` for debugging. Do not let exceptions propagate out of `_handle_message` — the WebSocket loop must stay alive.

```python
except Exception:
    logger.exception("[%s] Error handling message", self.session_id)
    await self.send({"type": "ERROR", "data": {"message": "Internal error"}})
```

### Unknown commands → `ERROR`

Unrecognized command names return `ERROR` with a descriptive message. This handles orchestrator/agent version mismatches gracefully — the user agent learns what went wrong and can report it.

---

## 10. How to Fork This Agent

Follow these steps to turn this codebase into your own service agent:

**Step 1 — Replace the service logic**

Delete `src/summarizer.py` and create your own service module. Your module needs one public async function:

```python
async def run_my_service(input_data: str) -> str:
    ...
```

**Step 2 — Update the capability document**

Edit `src/capabilities.py`. The capability document is read by LLMs — write it in clear natural language. Include:
- What your service does
- Every command, its input shape, and its output shape
- Your price
- Validation constraints

**Step 3 — Update command handlers**

In `src/command_handlers.py`:
- Replace `_handle_summarize` with your command logic
- Update `SUMMARIZATION_PRICE` to your price
- Update `MAX_DOCUMENT_LENGTH` or remove it if not applicable
- Register new commands in the `handlers` dict

**Step 4 — Update config and env**

Edit `src/config.py` if you need additional settings. Add them to `.env.example` too.

**Step 5 — Update README**

Update the README with your agent's name, description, and any extra setup steps.

**Step 6 — Run the tests**

Update `tests/test_handlers.py` for your new commands. The test for capabilities, payment verifier, and the summarizer pattern are all reusable — adjust the expected command names and outputs.

**Step 7 — Deploy and register**

See the Registration section in [README.md](README.md).

---

## Module Reference

| File | Role |
|---|---|
| `src/main.py` | FastAPI app, HTTP endpoints, lifespan |
| `src/capabilities.py` | Capability document (constant string) |
| `src/config.py` | Pydantic settings from environment |
| `src/models.py` | Pydantic request/response models |
| `src/session_manager.py` | In-memory session state store |
| `src/orchestrator_ws.py` | WebSocket client that dials back to orchestrator |
| `src/command_handlers.py` | All command routing and business logic |
| `src/summarizer.py` | Claude-powered summarization (replace this) |
| `src/payment_verifier.py` | Payment verification (escrow trust model) |
