# Web Scraper Service Agent Architecture

This agent follows the same service-agent architecture as the canonical
document-summarizer example:

1. The marketplace/orchestrator reads `GET /capabilities`.
2. The orchestrator calls `POST /connect` with a session id and WebSocket auth.
3. The agent creates session state and dials back to the orchestrator WebSocket.
4. The orchestrator sends `scrape_url` or `extract_structured_data` commands over the WebSocket.
5. The agent requests payment, stores the pending URL request, and waits for
   `payment_confirmed`.
6. After payment confirmation, the agent fetches the page, extracts readable
   content or structured page data, and returns `JOB_DONE`.

## Reusable Files

| File | Role |
|---|---|
| `src/main.py` | FastAPI app, `/capabilities`, `/connect`, `/health` |
| `src/orchestrator_ws.py` | WebSocket dial-back client |
| `src/session_manager.py` | Per-session state, including pending scrape request |
| `src/payment_verifier.py` | Payment verification abstraction |
| `src/command_handlers.py` | Command routing, validation, payment gating |
| `src/scraper.py` | Web scraping implementation |
| `src/capabilities.py` | Capability document shown to user agents |

## Command Contract

### Scrape URL

Inbound:

```json
{
  "command": "scrape_url",
  "arguments": {
    "url": "https://example.com",
    "include_links": false,
    "max_chars": 20000
  }
}
```

### Extract Structured Data

Inbound:

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

Outbound after payment:

```json
{
  "type": "JOB_DONE",
  "data": {
    "details": {
      "url": "https://example.com",
      "status_code": 200,
      "title": "Example",
      "description": "Page description",
      "headings": [{"level": "h1", "text": "Example"}],
      "open_graph": {"og:title": "Example"},
      "twitter_card": {"twitter:card": "summary"},
      "json_ld": [{"@type": "Product", "name": "Example"}],
      "tables": [{"headers": ["Name"], "rows": [["Value"]]}],
      "links": [{"url": "https://example.com/a", "text": "A"}],
      "text_preview": "Readable text...",
      "text_length": 1200
    }
  }
}
```

Outbound after payment:

```json
{
  "type": "JOB_DONE",
  "data": {
    "details": {
      "url": "https://example.com",
      "status_code": 200,
      "title": "Example Domain",
      "description": "",
      "text": "Readable page text",
      "text_length": 1200,
      "returned_text_length": 1200,
      "truncated": false
    }
  }
}
```

The HTTP and WebSocket transport pattern should remain stable for future agents;
only the command handlers, capability document, session fields, and service
logic usually change.
