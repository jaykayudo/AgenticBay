# Research Service Agent Architecture

This agent follows the Agentic Bay service-agent pattern:

1. The orchestrator reads `GET /capabilities`.
2. The orchestrator calls `POST /connect`.
3. The agent dials back to the orchestrator WebSocket.
4. The orchestrator sends `research_topic`.
5. The agent requests payment and stores the pending research request.
6. After `payment_confirmed`, the agent fetches supplied sources, calls Claude,
   and returns `JOB_DONE`.

## Command Contract

Inbound:

```json
{
  "command": "research_topic",
  "arguments": {
    "topic": "research question",
    "sources": ["https://example.com/source"],
    "depth": "standard",
    "max_sources": 5
  }
}
```

Outbound after payment:

```json
{
  "type": "JOB_DONE",
  "data": {
    "details": {
      "topic": "research question",
      "depth": "standard",
      "sources_requested": 1,
      "sources_fetched": [{"url": "...", "title": "...", "error": ""}],
      "report": "{\"summary\": \"...\", \"key_findings\": [...]}"
    }
  }
}
```

## Module Reference

| File | Role |
|---|---|
| `src/main.py` | FastAPI app, `/capabilities`, `/connect`, `/health` |
| `src/orchestrator_ws.py` | WebSocket dial-back client |
| `src/session_manager.py` | Per-session state, including pending research request |
| `src/command_handlers.py` | Command routing, validation, payment gating |
| `src/researcher.py` | Source fetching and Claude research synthesis |
| `src/payment_verifier.py` | Payment verification abstraction |
| `src/capabilities.py` | Capability document shown to user agents |
