"""
Unit tests for OrchestratorLLM.

All tests bypass __init__ and replace self.client with an AsyncMock so no
real Anthropic API calls are ever made.

Covers:
  enrich_search_query  — strips whitespace, forwards raw query to LLM
  rerank_agents        — empty list, sorting by score, JSON parse fallback, merges match_reason
  find_payment_success_command — happy path, JSON parse fallback → default command
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.agents.orchestrator.llm import OrchestratorLLM

pytestmark = [pytest.mark.asyncio]


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_llm() -> OrchestratorLLM:
    """Construct OrchestratorLLM without __init__ and inject a mock client."""
    llm = OrchestratorLLM.__new__(OrchestratorLLM)
    llm.client = AsyncMock()
    return llm


def _llm_response(text: str) -> MagicMock:
    """Return a mock Anthropic Message whose first content block is a TextBlock."""
    from anthropic.types import TextBlock

    block = MagicMock(spec=TextBlock)
    block.text = text
    resp = MagicMock()
    resp.content = [block]
    return resp


# ═══════════════════════════════════════════════════════════════════════════════
# enrich_search_query
# ═══════════════════════════════════════════════════════════════════════════════


async def test_enrich_search_query_returns_stripped_text() -> None:
    llm = _make_llm()
    llm.client.messages.create = AsyncMock(
        return_value=_llm_response("  AI text summarization NLP service  ")
    )

    result = await llm.enrich_search_query("summarize text")

    assert result == "AI text summarization NLP service"


async def test_enrich_search_query_calls_llm_once() -> None:
    llm = _make_llm()
    llm.client.messages.create = AsyncMock(return_value=_llm_response("enriched"))

    await llm.enrich_search_query("my query")

    llm.client.messages.create.assert_called_once()


async def test_enrich_search_query_includes_raw_query_in_message() -> None:
    llm = _make_llm()
    llm.client.messages.create = AsyncMock(return_value=_llm_response("enriched"))

    await llm.enrich_search_query("my special raw query")

    call_kwargs = llm.client.messages.create.call_args.kwargs
    content = call_kwargs["messages"][0]["content"]
    assert "my special raw query" in content


async def test_enrich_search_query_uses_temperature_zero() -> None:
    llm = _make_llm()
    llm.client.messages.create = AsyncMock(return_value=_llm_response("q"))

    await llm.enrich_search_query("q")

    call_kwargs = llm.client.messages.create.call_args.kwargs
    assert call_kwargs.get("temperature") == 0


# ═══════════════════════════════════════════════════════════════════════════════
# rerank_agents
# ═══════════════════════════════════════════════════════════════════════════════


async def test_rerank_agents_empty_list_returns_empty_without_llm_call() -> None:
    llm = _make_llm()

    result = await llm.rerank_agents(original_query="find agent", agents=[])

    assert result == []
    llm.client.messages.create.assert_not_called()


async def test_rerank_agents_sorts_by_relevance_score_descending() -> None:
    llm = _make_llm()

    agents = [
        {"id": "a1", "name": "Low", "description": "d", "rating": 4.0, "pricing": {}},
        {"id": "a2", "name": "High", "description": "d", "rating": 4.5, "pricing": {}},
        {"id": "a3", "name": "Mid", "description": "d", "rating": 4.2, "pricing": {}},
    ]
    rankings = [
        {"id": "a1", "relevance_score": 0.3, "match_reason": "low"},
        {"id": "a2", "relevance_score": 0.9, "match_reason": "best"},
        {"id": "a3", "relevance_score": 0.6, "match_reason": "mid"},
    ]
    llm.client.messages.create = AsyncMock(return_value=_llm_response(json.dumps(rankings)))

    result = await llm.rerank_agents("query", agents)

    assert result[0]["id"] == "a2"
    assert result[1]["id"] == "a3"
    assert result[2]["id"] == "a1"


async def test_rerank_agents_merges_match_reason_into_agent() -> None:
    llm = _make_llm()

    agents = [{"id": "a1", "name": "X", "description": "d", "rating": 4.0, "pricing": {}}]
    rankings = [{"id": "a1", "relevance_score": 0.8, "match_reason": "perfect fit for data work"}]
    llm.client.messages.create = AsyncMock(return_value=_llm_response(json.dumps(rankings)))

    result = await llm.rerank_agents("query", agents)

    assert result[0]["match_reason"] == "perfect fit for data work"
    assert result[0]["relevance_score"] == 0.8


async def test_rerank_agents_returns_original_list_on_json_parse_error() -> None:
    llm = _make_llm()

    agents = [{"id": "a1", "name": "X", "description": "d", "rating": 4.0, "pricing": {}}]
    llm.client.messages.create = AsyncMock(
        return_value=_llm_response("this is definitely not JSON at all")
    )

    result = await llm.rerank_agents("query", agents)

    assert result == agents


async def test_rerank_agents_preserves_all_original_agent_fields() -> None:
    llm = _make_llm()

    agents = [
        {
            "id": "a1",
            "name": "DataBot",
            "description": "Analyzes data",
            "rating": 4.9,
            "pricing": {"task": 20},
            "similarity_score": 0.91,
        }
    ]
    rankings = [{"id": "a1", "relevance_score": 0.9, "match_reason": "good"}]
    llm.client.messages.create = AsyncMock(return_value=_llm_response(json.dumps(rankings)))

    result = await llm.rerank_agents("query", agents)

    assert result[0]["name"] == "DataBot"
    assert result[0]["rating"] == 4.9
    assert result[0]["pricing"] == {"task": 20}


async def test_rerank_agents_skips_ids_not_in_original_list() -> None:
    """LLM may hallucinate extra agent IDs — they must be silently ignored."""
    llm = _make_llm()

    agents = [{"id": "real-id", "name": "X", "description": "d", "rating": 4.0, "pricing": {}}]
    rankings = [
        {"id": "real-id", "relevance_score": 0.8, "match_reason": "ok"},
        {"id": "hallucinated-id", "relevance_score": 1.0, "match_reason": "fake"},
    ]
    llm.client.messages.create = AsyncMock(return_value=_llm_response(json.dumps(rankings)))

    result = await llm.rerank_agents("query", agents)

    assert len(result) == 1
    assert result[0]["id"] == "real-id"


# ═══════════════════════════════════════════════════════════════════════════════
# find_payment_success_command
# ═══════════════════════════════════════════════════════════════════════════════


async def test_find_payment_success_command_returns_parsed_command() -> None:
    llm = _make_llm()
    expected = {
        "command": "CONFIRM_PAYMENT",
        "arguments_template": {"invoice_id": "<invoice_id>"},
    }
    llm.client.messages.create = AsyncMock(return_value=_llm_response(json.dumps(expected)))

    result = await llm.find_payment_success_command("capability document text")

    assert result["command"] == "CONFIRM_PAYMENT"
    assert "invoice_id" in result["arguments_template"]


async def test_find_payment_success_command_passes_capabilities_to_llm() -> None:
    llm = _make_llm()
    caps = "PAYMENT_SUCCESSFUL command: send invoice_id and contract address"
    llm.client.messages.create = AsyncMock(
        return_value=_llm_response(json.dumps({"command": "X", "arguments_template": {}}))
    )

    await llm.find_payment_success_command(caps)

    call_kwargs = llm.client.messages.create.call_args.kwargs
    assert caps in call_kwargs["messages"][0]["content"]


async def test_find_payment_success_command_defaults_on_json_parse_error() -> None:
    llm = _make_llm()
    llm.client.messages.create = AsyncMock(return_value=_llm_response("this is not valid JSON!!!"))

    result = await llm.find_payment_success_command("caps doc")

    assert result["command"] == "PAYMENT_SUCCESSFUL"
    assert "invoice_id" in result["arguments_template"]


async def test_find_payment_success_command_default_has_invoice_contract() -> None:
    llm = _make_llm()
    llm.client.messages.create = AsyncMock(return_value=_llm_response("bad output"))

    result = await llm.find_payment_success_command("caps")

    assert "invoice_contract" in result["arguments_template"]
