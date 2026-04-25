"""
Tests for OrchestratorAgent._handle_search (SEARCH_AGENT message).

Covers:
  - Happy path: query enriched → vector search → LLM reranking → SearchAgentResponse
  - Phase transitions to SEARCHING
  - Enriched query forwarded to vector search (not the raw one)
  - Original query forwarded to the reranker (not the enriched one)
  - Empty result set returned correctly
  - LLM failure returns ERROR(search_error)
  - Vector search failure returns ERROR(search_error)
"""

from __future__ import annotations

import json
import uuid

import pytest

from tests.test_orchestrator_agent.conftest import (
    FakeSend,
    FakeSessionStore,
    build_orchestrator,
    make_state,
)
from app.agents.orchestrator.schema import SessionPhase

pytestmark = [pytest.mark.asyncio]


def _raw_search(message: str) -> str:
    return json.dumps({"type": "SEARCH_AGENT", "data": {"message": message}})


def _make_agent_dict(agent_id: str | None = None, **kwargs: object) -> dict:
    return {
        "id": agent_id or str(uuid.uuid4()),
        "name": kwargs.get("name", "TestBot"),
        "description": kwargs.get("description", "Does things"),
        "rating": kwargs.get("rating", 4.5),
        "pricing": kwargs.get("pricing", {}),
    }


# ── Happy path ────────────────────────────────────────────────────────────────


async def test_search_sends_agent_list_to_user() -> None:
    store = FakeSessionStore()
    state = make_state()
    await store.save(state)
    orch = build_orchestrator(store)
    send = FakeSend()

    agent_id = str(uuid.uuid4())
    agents = [_make_agent_dict(agent_id, name="DataBot")]

    orch.llm.enrich_search_query.return_value = "data analysis enriched"
    orch.vector_search.search.return_value = agents
    orch.llm.rerank_agents.return_value = agents

    await orch.handle_message(state.session_id, _raw_search("analyze my data"), send)

    results = send.of_type("SEARCH_AGENT")
    assert len(results) == 1
    returned_agents = results[0]["data"]["agents"]
    assert len(returned_agents) == 1
    assert returned_agents[0]["id"] == agent_id
    assert returned_agents[0]["name"] == "DataBot"


async def test_search_response_includes_next_suggested_command() -> None:
    store = FakeSessionStore()
    state = make_state()
    await store.save(state)
    orch = build_orchestrator(store)
    send = FakeSend()

    orch.llm.enrich_search_query.return_value = "q"
    orch.vector_search.search.return_value = []
    orch.llm.rerank_agents.return_value = []

    await orch.handle_message(state.session_id, _raw_search("find agent"), send)

    result = send.of_type("SEARCH_AGENT")[0]
    assert result["data"]["next_suggested_command"] == "CONNECT_AGENT"


# ── Phase transition ──────────────────────────────────────────────────────────


async def test_search_sets_phase_to_searching() -> None:
    store = FakeSessionStore()
    state = make_state()
    await store.save(state)
    orch = build_orchestrator(store)
    send = FakeSend()

    orch.llm.enrich_search_query.return_value = "q"
    orch.vector_search.search.return_value = []
    orch.llm.rerank_agents.return_value = []

    await orch.handle_message(state.session_id, _raw_search("find"), send)

    saved = await store.get(state.session_id)
    assert saved.phase == SessionPhase.SEARCHING


# ── LLM / vector search wiring ────────────────────────────────────────────────


async def test_search_passes_enriched_query_to_vector_search() -> None:
    store = FakeSessionStore()
    state = make_state()
    await store.save(state)
    orch = build_orchestrator(store)
    send = FakeSend()

    orch.llm.enrich_search_query.return_value = "AI text summarization NLP service"
    orch.vector_search.search.return_value = []
    orch.llm.rerank_agents.return_value = []

    await orch.handle_message(state.session_id, _raw_search("summarize text"), send)

    orch.vector_search.search.assert_called_once()
    call_kwargs = orch.vector_search.search.call_args.kwargs
    assert call_kwargs["query"] == "AI text summarization NLP service"
    assert call_kwargs["top_k"] == 10


async def test_search_passes_original_query_to_reranker() -> None:
    store = FakeSessionStore()
    state = make_state()
    await store.save(state)
    orch = build_orchestrator(store)
    send = FakeSend()

    agents = [_make_agent_dict()]
    orch.llm.enrich_search_query.return_value = "enriched version"
    orch.vector_search.search.return_value = agents
    orch.llm.rerank_agents.return_value = agents

    await orch.handle_message(state.session_id, _raw_search("original user query"), send)

    orch.llm.rerank_agents.assert_called_once()
    call_kwargs = orch.llm.rerank_agents.call_args.kwargs
    assert call_kwargs["original_query"] == "original user query"


async def test_search_passes_vector_results_to_reranker() -> None:
    store = FakeSessionStore()
    state = make_state()
    await store.save(state)
    orch = build_orchestrator(store)
    send = FakeSend()

    raw_agents = [_make_agent_dict(), _make_agent_dict()]
    orch.llm.enrich_search_query.return_value = "q"
    orch.vector_search.search.return_value = raw_agents
    orch.llm.rerank_agents.return_value = raw_agents

    await orch.handle_message(state.session_id, _raw_search("find"), send)

    call_kwargs = orch.llm.rerank_agents.call_args.kwargs
    assert call_kwargs["agents"] == raw_agents


# ── Edge cases ────────────────────────────────────────────────────────────────


async def test_search_returns_empty_agent_list_when_nothing_found() -> None:
    store = FakeSessionStore()
    state = make_state()
    await store.save(state)
    orch = build_orchestrator(store)
    send = FakeSend()

    orch.llm.enrich_search_query.return_value = "enriched"
    orch.vector_search.search.return_value = []
    orch.llm.rerank_agents.return_value = []

    await orch.handle_message(state.session_id, _raw_search("find nonexistent"), send)

    result = send.of_type("SEARCH_AGENT")[0]
    assert result["data"]["agents"] == []


async def test_search_returns_multiple_reranked_agents_in_order() -> None:
    store = FakeSessionStore()
    state = make_state()
    await store.save(state)
    orch = build_orchestrator(store)
    send = FakeSend()

    id_a, id_b = str(uuid.uuid4()), str(uuid.uuid4())
    reranked = [_make_agent_dict(id_a, name="Best"), _make_agent_dict(id_b, name="Second")]
    orch.llm.enrich_search_query.return_value = "q"
    orch.vector_search.search.return_value = reranked
    orch.llm.rerank_agents.return_value = reranked

    await orch.handle_message(state.session_id, _raw_search("find"), send)

    agents = send.of_type("SEARCH_AGENT")[0]["data"]["agents"]
    assert agents[0]["id"] == id_a
    assert agents[1]["id"] == id_b


# ── Error paths ───────────────────────────────────────────────────────────────


async def test_search_returns_search_error_on_llm_failure() -> None:
    store = FakeSessionStore()
    state = make_state()
    await store.save(state)
    orch = build_orchestrator(store)
    send = FakeSend()

    orch.llm.enrich_search_query.side_effect = RuntimeError("LLM unavailable")

    await orch.handle_message(state.session_id, _raw_search("find"), send)

    errors = send.of_type("ERROR")
    assert len(errors) == 1
    assert errors[0]["data"]["error_type"] == "search_error"


async def test_search_returns_search_error_on_vector_search_failure() -> None:
    store = FakeSessionStore()
    state = make_state()
    await store.save(state)
    orch = build_orchestrator(store)
    send = FakeSend()

    orch.llm.enrich_search_query.return_value = "enriched"
    orch.vector_search.search.side_effect = ConnectionError("DB down")

    await orch.handle_message(state.session_id, _raw_search("find"), send)

    errors = send.of_type("ERROR")
    assert errors[0]["data"]["error_type"] == "search_error"


async def test_search_returns_search_error_on_rerank_failure() -> None:
    store = FakeSessionStore()
    state = make_state()
    await store.save(state)
    orch = build_orchestrator(store)
    send = FakeSend()

    orch.llm.enrich_search_query.return_value = "q"
    orch.vector_search.search.return_value = [_make_agent_dict()]
    orch.llm.rerank_agents.side_effect = RuntimeError("rerank failed")

    await orch.handle_message(state.session_id, _raw_search("find"), send)

    errors = send.of_type("ERROR")
    assert errors[0]["data"]["error_type"] == "search_error"
