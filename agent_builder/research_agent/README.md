# Research Agent

FastAPI service for a research agent that uses the shared `agent_sdk` package and returns a structured research report.

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

The local install in `requirements.txt` also installs the shared `agent_sdk` package from the parent `web/agents` directory, so future agents can reuse the same endpoints and runtime.

With the current SDK shape, an agent creator mainly writes one logic class that:
- declares the input model
- declares a few metadata fields
- implements `run(...)`

The SDK derives the standard endpoints, runtime wiring, input validation, and capability manifest from that class.

## Configure Hugging Face

Copy `.env.example` into `.env`, create a Hugging Face token with Inference Providers permission, then set:

```bash
HF_TOKEN=hf_your_token_here
HF_MODEL=katanemo/Arch-Router-1.5B:hf-inference
```

## Run

```bash
uvicorn app.main:app --reload
```

## Deploy

```bash
deploy-agent
```

The deploy command validates the standard endpoints and the capabilities manifest before it attempts to publish the service to Cloud Run.

The API will be available at `http://127.0.0.1:8000`, with docs at `/docs`.

## Example Request

```bash
curl -X POST http://127.0.0.1:8000/invoke/demo-session ^
  -H "Content-Type: application/json" ^
  -d "{\"capabilityId\":\"research_topic\",\"input\":{\"topic\":\"Artificial intelligence in drug discovery\",\"depth\":\"high\"}}"
```

For single-capability agents like this one, the SDK also accepts a shortcut payload like `{"topic":"...","depth":"high"}` and routes it to the only exposed capability automatically.

The current implementation stores runtime state in memory and processes one job at a time.
