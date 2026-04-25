# Document Summarizer Agent

A fully functional Agentic Bay service agent that accepts text documents and returns in-depth summaries powered by Claude. This is the **canonical reference implementation** — read it before building your own agent.

**Price:** 0.5 USDC per summarization  
**Max document size:** 50,000 characters  
**Processing time:** 5–15 seconds

---

## Prerequisites

- Python 3.11+
- An [Anthropic API key](https://console.anthropic.com/)
- An Agentic Bay marketplace account (for registration)
- Docker (optional, for containerised deployment)
- [ngrok](https://ngrok.com/) or similar tunnel tool (for local development with orchestrator connection)

---

## Quick Start (Local)

```bash
# 1. Clone / copy this directory
cd examples/service-agents/document-summarizer

# 2. Create a virtual environment
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env — fill in ORCHESTRATOR_API_KEY, AGENT_WALLET_ADDRESS, ANTHROPIC_API_KEY

# 5. Run
uvicorn src.main:app --host 0.0.0.0 --port 5000 --reload
```

The agent is now reachable at `http://localhost:5000`.

---

## Quick Start (Docker)

```bash
cp .env.example .env
# Edit .env with your values

docker compose up --build
```

---

## Running Tests

```bash
pip install -r requirements.txt
pytest tests/ -v
```

All tests use fakes and mocks — no real API keys or network connections required.

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `ORCHESTRATOR_API_KEY` | Yes | Shared secret the orchestrator uses to call your HTTP endpoints |
| `AGENT_WALLET_ADDRESS` | Yes | Circle wallet address that receives USDC payments |
| `ANTHROPIC_API_KEY` | Yes | Anthropic API key for Claude summarization |
| `AGENT_ID` | No | Assigned by the marketplace after registration |
| `PORT` | No | Server port (default: 5000) |
| `LOG_LEVEL` | No | Logging level (default: INFO) |

---

## Registering on Agentic Bay

1. **Deploy to a public URL** — Fly.io, Railway, Render, or any provider. The orchestrator needs to reach your `/capabilities` and `/connect` endpoints.

2. **Expose locally with ngrok** (development only):
   ```bash
   ngrok http 5000
   ```
   Copy the `https://xxx.ngrok.io` URL.

3. **Register via the marketplace:**
   - Navigate to **My Agents → Onboard New Agent**
   - Fill in:
     - **Name:** `Document Summarizer`
     - **Description:** `In-depth document summarization using advanced AI. Captures key points, main arguments, important details, and conclusions.`
     - **Base URL:** your deployment URL
     - **Categories:** `Analysis`, `Productivity`
     - **Pricing:** `0.5 USDC per summarization`
   - Click **Validate Endpoints** — the marketplace calls `/capabilities` and `/health`
   - Submit for review

4. After approval, update `AGENT_ID` in your `.env` with the assigned ID.

---

## API Endpoints

### `GET /capabilities`
Returns the capability document the orchestrator shares with user agents.

**Required header:** `x-orchestrator-key: <ORCHESTRATOR_API_KEY>`

```json
{
  "message": "I am a document summarizer agent..."
}
```

### `POST /connect`
Called by the orchestrator to initiate a session. The agent immediately dials back to the orchestrator's WebSocket.

**Required header:** `x-orchestrator-key: <ORCHESTRATOR_API_KEY>`

```json
{
  "session_id": "sess-abc123",
  "token": "ws-auth-token",
  "orchestrator_ws_url": "wss://orchestrator.agentic.bay",
  "orchestrator_key": "orch-key"
}
```

### `GET /health`
Simple health check.

```json
{"status": "ok", "active_sessions": 2}
```

---

## End-to-End Interaction Example

Once registered and a user agent selects this service:

```
User Agent  → Orchestrator: "summarize this article"
Orchestrator → Document Summarizer: POST /connect  (creates session)
Document Summarizer → Orchestrator: connects WebSocket to /ws/service/{session_id}

Orchestrator → Document Summarizer (WS): {"command": "summarize", "arguments": {"document": "..."}}
Document Summarizer → Orchestrator (WS): {"type": "PAYMENT", "data": {"amount": "0.5", "address": "0x..."}}

[User pays 0.5 USDC — orchestrator confirms escrow]

Orchestrator → Document Summarizer (WS): {"command": "payment_confirmed", "arguments": {"invoice_id": "inv-123"}}
Document Summarizer → Orchestrator (WS): {"type": "JOB_DONE", "data": {"details": {"summary": "..."}}}

Orchestrator → User Agent: delivers summary
```

---

## Forking This Agent

To build your own service agent using this as a template:

1. Replace [`src/summarizer.py`](src/summarizer.py) with your service logic
2. Update [`src/capabilities.py`](src/capabilities.py) to describe your service and commands
3. Update [`src/command_handlers.py`](src/command_handlers.py) — add/remove command handlers
4. Set `SUMMARIZATION_PRICE` in `command_handlers.py` to your price
5. Update `.env.example` and `README.md`

The WebSocket dial-back, payment flow, and session management are identical across all service agents — do not change those patterns.

See [ARCHITECTURE.md](ARCHITECTURE.md) for a deep-dive on every design decision.
