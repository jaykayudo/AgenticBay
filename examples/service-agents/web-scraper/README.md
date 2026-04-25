# Web Scraper Agent

A fully functional Agentic Bay service agent that accepts a public web page URL
and returns clean page text, metadata, and optional links.

**Price:** 0.2 USDC per scrape or structured extraction  
**Max returned text:** 50,000 characters  
**Default returned text:** 20,000 characters  
**Processing time:** usually 2-15 seconds

---

## Prerequisites

- Python 3.11+
- An Agentic Bay marketplace account
- Docker (optional, for containerised deployment)
- ngrok or similar tunnel tool for local development with orchestrator connection

---

## Quick Start

```bash
cd examples/service-agents/web-scraper
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env and fill in ORCHESTRATOR_API_KEY and AGENT_WALLET_ADDRESS
uvicorn src.main:app --host 0.0.0.0 --port 5000 --reload
```

The agent is now reachable at `http://localhost:5000`.

---

## Docker

```bash
cp .env.example .env
# Edit .env with your values
docker compose up --build
```

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `ORCHESTRATOR_API_KEY` | Yes | Shared secret the orchestrator uses to call your HTTP endpoints |
| `AGENT_WALLET_ADDRESS` | Yes | Wallet address that receives USDC payments |
| `AGENT_ID` | No | Assigned by the marketplace after registration |
| `PORT` | No | Server port, default `5000` |
| `LOG_LEVEL` | No | Logging level, default `INFO` |
| `SCRAPER_TIMEOUT_SECONDS` | No | HTTP fetch timeout, default `15` |
| `SCRAPER_MAX_RESPONSE_BYTES` | No | Maximum response size, default `2000000` |

---

## API Endpoints

### `GET /capabilities`

Returns the capability document.

**Required header:** `x-orchestrator-key: <ORCHESTRATOR_API_KEY>`

### `POST /connect`

Called by the orchestrator to initiate a session. The agent immediately dials
back to the orchestrator's WebSocket.

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

---

## WebSocket Commands

### Scrape URL

```json
{
  "command": "scrape_url",
  "arguments": {
    "url": "https://example.com",
    "include_links": true,
    "max_chars": 20000
  }
}
```

### Extract Structured Data

```json
{
  "command": "extract_structured_data",
  "arguments": {
    "url": "https://example.com",
    "include_links": true,
    "include_tables": true,
    "include_json_ld": true
  }
}
```

This returns page metadata, headings, Open Graph tags, Twitter card tags,
JSON-LD, HTML tables, links, and a short text preview.

Each command returns a `PAYMENT` response first. After payment is confirmed, the
orchestrator sends:

```json
{
  "command": "payment_confirmed",
  "arguments": {"invoice_id": "inv-123"}
}
```

The agent then processes the pending URL and returns `JOB_DONE`.

---

## Running Tests

```bash
pip install -r requirements.txt
pytest tests/ -v
```

Tests use fakes and mocks, so they do not make real network calls.
