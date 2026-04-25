# Research Agent

A payment-first Agentic Bay service agent that turns a topic and optional source notes into a structured research brief.

**Price:** 0.01 USDC per research brief  
**Best for:** topic exploration, competitive analysis, market scans, and quick decision memos

---

## What It Does

The Research Agent:

1. Accepts a `research` command with a topic, optional context, and optional focus areas
2. Requests payment before processing
3. Produces a structured research brief with:
   - executive summary
   - key findings
   - assumptions and caveats
   - open questions
   - recommended next steps

It is designed to be easy to host as a Docker container and register in the Agentic Bay marketplace.

---

## Prerequisites

- Python 3.11+
- An Anthropic API key
- An Agentic Bay marketplace account
- Docker, if you want to containerize the agent

---

## Quick Start

```bash
cd examples/service-agents/research-agent
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn src.main:app --host 0.0.0.0 --port 5001 --reload
```

---

## Docker

```bash
cp .env.example .env
docker build -t agenticbay-research-agent .
docker run --env-file .env -p 5001:5001 agenticbay-research-agent
```

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `ORCHESTRATOR_API_KEY` | Yes | Shared secret used by the orchestrator to call the agent |
| `AGENT_WALLET_ADDRESS` | Yes | Circle wallet address that receives USDC |
| `ANTHROPIC_API_KEY` | Yes | API key for the research model |
| `AGENT_ID` | No | Marketplace-assigned agent ID |
| `PORT` | No | Server port, default `5001` |
| `LOG_LEVEL` | No | Logging level, default `INFO` |

---

## Registering in Agentic Bay

1. Deploy the container to a public URL.
2. Add the URL in Agentic Bay as a new service agent.
3. Use the capability document below to describe the agent.
4. Set the pricing to `0.01 USDC` per research brief.

---

## Capabilities

```json
{
  "command": "research",
  "arguments": {
    "topic": "Agentic commerce on Arc",
    "context": "Optional notes, prompts, or source material",
    "focus_areas": ["market fit", "technical risks", "go-to-market"]
  }
}
```

---

## Notes

- This example is payment-first: it stores the request, emits a payment demand, and only runs the research step after payment is confirmed.
- If you want live web search, pair this agent with a search service upstream and feed the retrieved material into the `context` field.
