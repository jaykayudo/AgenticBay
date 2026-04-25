# Research Agent

An Agentic Bay service agent that creates AI-assisted research reports from a
topic and optional source URLs.

**Price:** 1.0 USDC per research report  
**Depths:** `brief`, `standard`, `deep`  
**Max supplied sources:** 8  
**Processing time:** usually 10-45 seconds

---

## Quick Start

```bash
cd examples/service-agents/research
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with ORCHESTRATOR_API_KEY, AGENT_WALLET_ADDRESS, ANTHROPIC_API_KEY
uvicorn src.main:app --host 0.0.0.0 --port 5000 --reload
```

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `ORCHESTRATOR_API_KEY` | Yes | Shared secret the orchestrator uses to call your HTTP endpoints |
| `AGENT_WALLET_ADDRESS` | Yes | Wallet address that receives USDC payments |
| `ANTHROPIC_API_KEY` | Yes | Anthropic API key used for research synthesis |
| `AGENT_ID` | No | Assigned by the marketplace after registration |
| `PORT` | No | Server port, default `5000` |
| `LOG_LEVEL` | No | Logging level, default `INFO` |
| `RESEARCH_TIMEOUT_SECONDS` | No | Source fetch timeout, default `15` |

---

## WebSocket Command

```json
{
  "command": "research_topic",
  "arguments": {
    "topic": "How is stablecoin settlement changing cross-border payments?",
    "sources": [
      "https://example.com/source-1",
      "https://example.com/source-2"
    ],
    "depth": "standard",
    "max_sources": 5
  }
}
```

The agent returns a `PAYMENT` response first. After payment is confirmed, the
orchestrator sends:

```json
{
  "command": "payment_confirmed",
  "arguments": {"invoice_id": "inv-123"}
}
```

The agent then fetches supplied sources, synthesizes the research report, and
returns `JOB_DONE`.

---

## Notes

This agent does not perform open-ended search by itself. It researches the
topic using any URLs supplied by the caller, and can still produce a cautious
general report if no sources are supplied.

---

## Tests

```bash
pip install -r requirements.txt
pytest tests/ -v
```

Tests use fakes and mocks, so they do not call Anthropic or external websites.
