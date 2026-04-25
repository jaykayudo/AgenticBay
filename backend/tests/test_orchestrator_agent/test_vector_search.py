"""
Unit tests for VectorSearch.

Voyage AI client and asyncpg connections are fully mocked — no real
network calls or database queries are made.

Covers:
  search()       — happy path, empty results, Voyage API error, DB error,
                   input_type="query" used for embedding, top_k respected
  index_agent()  — happy path returns agent_id, error returns None
  remove_agent() — happy path returns True, error returns False
"""

from __future__ import annotations

import json
import uuid
from contextlib import asynccontextmanager
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.orchestrator.vector_search import VectorSearch

pytestmark = [pytest.mark.asyncio]


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_vs() -> VectorSearch:
    """Construct VectorSearch without __init__; _vo is set to an AsyncMock."""
    vs = VectorSearch.__new__(VectorSearch)
    vs._vo = AsyncMock()
    return vs


def _voyage_result(embedding: list[float]) -> MagicMock:
    result = MagicMock()
    result.embeddings = [embedding]
    return result


def _fake_conn(rows: list[dict[str, Any]] | None = None, execute_ok: bool = True):
    """Return an async context manager that yields a fake asyncpg connection."""
    rows = rows or []

    # Build mock Record objects with dict-style access
    fake_rows = []
    for row in rows:
        record = MagicMock()
        record.__getitem__ = lambda self, key, r=row: r[key]
        fake_rows.append(record)

    conn = AsyncMock()
    conn.fetch = AsyncMock(return_value=fake_rows)
    conn.execute = AsyncMock()

    @asynccontextmanager
    async def _ctx():
        yield conn

    return _ctx, conn


def _failing_conn(exc: Exception):
    """Return an async context manager whose fetch/execute raises exc."""

    @asynccontextmanager
    async def _ctx():
        conn = AsyncMock()
        conn.fetch = AsyncMock(side_effect=exc)
        conn.execute = AsyncMock(side_effect=exc)
        yield conn

    return _ctx


# ═══════════════════════════════════════════════════════════════════════════════
# search()
# ═══════════════════════════════════════════════════════════════════════════════


async def test_search_returns_agent_list_on_success() -> None:
    vs = _make_vs()
    embedding = [0.1, 0.2, 0.3]
    agent_id = str(uuid.uuid4())

    vs._vo.embed = AsyncMock(return_value=_voyage_result(embedding))

    db_rows = [
        {
            "agent_id": agent_id,
            "name": "DataBot",
            "description": "Analyzes data",
            "category": "analytics",
            "tags": ["data", "ml"],
            "rating": 4.8,
            "pricing": json.dumps({"analysis": 20}),
            "similarity_score": 0.95,
        }
    ]
    ctx, _ = _fake_conn(db_rows)

    with patch("app.agents.orchestrator.vector_search.asyncpg_connection", ctx):
        results = await vs.search("find data agent")

    assert len(results) == 1
    assert results[0]["id"] == agent_id
    assert results[0]["name"] == "DataBot"
    assert results[0]["similarity_score"] == 0.95


async def test_search_returns_empty_list_when_no_matches() -> None:
    vs = _make_vs()
    vs._vo.embed = AsyncMock(return_value=_voyage_result([0.0] * 128))

    ctx, _ = _fake_conn([])  # empty rows

    with patch("app.agents.orchestrator.vector_search.asyncpg_connection", ctx):
        results = await vs.search("unlikely query")

    assert results == []


async def test_search_parses_jsonb_pricing_string() -> None:
    """asyncpg sometimes returns JSONB columns as strings; VectorSearch must parse them."""
    vs = _make_vs()
    vs._vo.embed = AsyncMock(return_value=_voyage_result([0.1]))

    db_rows = [
        {
            "agent_id": str(uuid.uuid4()),
            "name": "X",
            "description": "Y",
            "category": "cat",
            "tags": [],
            "rating": 4.0,
            "pricing": '{"task": 10}',  # JSON string as returned by asyncpg
            "similarity_score": 0.8,
        }
    ]
    ctx, _ = _fake_conn(db_rows)

    with patch("app.agents.orchestrator.vector_search.asyncpg_connection", ctx):
        results = await vs.search("query")

    assert results[0]["pricing"] == {"task": 10}


async def test_search_returns_empty_list_on_voyage_error() -> None:
    vs = _make_vs()
    vs._vo.embed = AsyncMock(side_effect=RuntimeError("Voyage API unavailable"))

    results = await vs.search("query")

    assert results == []


async def test_search_returns_empty_list_on_db_error() -> None:
    vs = _make_vs()
    vs._vo.embed = AsyncMock(return_value=_voyage_result([0.1, 0.2]))

    ctx = _failing_conn(ConnectionError("DB unavailable"))

    with patch("app.agents.orchestrator.vector_search.asyncpg_connection", ctx):
        results = await vs.search("query")

    assert results == []


async def test_search_embeds_with_query_input_type() -> None:
    vs = _make_vs()
    vs._vo.embed = AsyncMock(return_value=_voyage_result([0.1] * 64))

    ctx, _ = _fake_conn([])

    with patch("app.agents.orchestrator.vector_search.asyncpg_connection", ctx):
        await vs.search("test query")

    vs._vo.embed.assert_called_once()
    call_kwargs = vs._vo.embed.call_args.kwargs
    assert call_kwargs.get("input_type") == "query"


async def test_search_passes_text_to_embed() -> None:
    vs = _make_vs()
    vs._vo.embed = AsyncMock(return_value=_voyage_result([0.0]))

    ctx, _ = _fake_conn([])

    with patch("app.agents.orchestrator.vector_search.asyncpg_connection", ctx):
        await vs.search("specific query text")

    call_kwargs = vs._vo.embed.call_args.kwargs
    assert "specific query text" in call_kwargs.get("texts", [])


async def test_search_respects_top_k_parameter() -> None:
    vs = _make_vs()
    vs._vo.embed = AsyncMock(return_value=_voyage_result([0.1] * 32))

    ctx, conn_mock = _fake_conn([])

    with patch("app.agents.orchestrator.vector_search.asyncpg_connection", ctx):
        await vs.search("query", top_k=3)

    call_args = conn_mock.fetch.call_args[0]
    # top_k ($2) is passed as the second positional parameter to fetch
    assert 3 in call_args


async def test_search_default_top_k_is_ten() -> None:
    vs = _make_vs()
    vs._vo.embed = AsyncMock(return_value=_voyage_result([0.0] * 16))

    ctx, conn_mock = _fake_conn([])

    with patch("app.agents.orchestrator.vector_search.asyncpg_connection", ctx):
        await vs.search("query")

    call_args = conn_mock.fetch.call_args[0]
    assert 10 in call_args


# ═══════════════════════════════════════════════════════════════════════════════
# index_agent()
# ═══════════════════════════════════════════════════════════════════════════════


async def test_index_agent_returns_agent_id_on_success() -> None:
    vs = _make_vs()
    agent_id = str(uuid.uuid4())

    vs._vo.embed = AsyncMock(return_value=_voyage_result([0.1] * 128))

    ctx, _ = _fake_conn()

    with patch("app.agents.orchestrator.vector_search.asyncpg_connection", ctx):
        result = await vs.index_agent({
            "id": agent_id,
            "name": "TestBot",
            "description": "Does things",
            "avg_rating": 4.5,
            "pricing_summary": {"task": 10},
            "category": "automation",
            "tags": ["ml"],
        })

    assert result == agent_id


async def test_index_agent_embeds_with_document_input_type() -> None:
    vs = _make_vs()
    agent_id = str(uuid.uuid4())
    vs._vo.embed = AsyncMock(return_value=_voyage_result([0.0] * 64))

    ctx, _ = _fake_conn()

    with patch("app.agents.orchestrator.vector_search.asyncpg_connection", ctx):
        await vs.index_agent({"id": agent_id, "name": "X", "description": "Y"})

    call_kwargs = vs._vo.embed.call_args.kwargs
    assert call_kwargs.get("input_type") == "document"


async def test_index_agent_embeds_name_and_description() -> None:
    vs = _make_vs()
    vs._vo.embed = AsyncMock(return_value=_voyage_result([0.0]))

    ctx, _ = _fake_conn()

    with patch("app.agents.orchestrator.vector_search.asyncpg_connection", ctx):
        await vs.index_agent({"id": "x", "name": "AgentName", "description": "The description"})

    call_kwargs = vs._vo.embed.call_args.kwargs
    embedded_text = call_kwargs.get("texts", [""])[0]
    assert "AgentName" in embedded_text
    assert "The description" in embedded_text


async def test_index_agent_returns_none_on_voyage_error() -> None:
    vs = _make_vs()
    vs._vo.embed = AsyncMock(side_effect=RuntimeError("embed failed"))

    result = await vs.index_agent({"id": "x", "name": "X", "description": "Y"})

    assert result is None


async def test_index_agent_returns_none_on_db_error() -> None:
    vs = _make_vs()
    vs._vo.embed = AsyncMock(return_value=_voyage_result([0.1]))

    ctx = _failing_conn(RuntimeError("insert failed"))

    with patch("app.agents.orchestrator.vector_search.asyncpg_connection", ctx):
        result = await vs.index_agent({"id": "x", "name": "X", "description": "Y"})

    assert result is None


# ═══════════════════════════════════════════════════════════════════════════════
# remove_agent()
# ═══════════════════════════════════════════════════════════════════════════════


async def test_remove_agent_returns_true_on_success() -> None:
    vs = _make_vs()
    ctx, conn_mock = _fake_conn()

    with patch("app.agents.orchestrator.vector_search.asyncpg_connection", ctx):
        result = await vs.remove_agent("agent-123")

    assert result is True
    conn_mock.execute.assert_called_once()


async def test_remove_agent_issues_delete_with_agent_id() -> None:
    vs = _make_vs()
    ctx, conn_mock = _fake_conn()

    with patch("app.agents.orchestrator.vector_search.asyncpg_connection", ctx):
        await vs.remove_agent("my-agent-id")

    call_args = conn_mock.execute.call_args[0]
    assert "my-agent-id" in call_args


async def test_remove_agent_returns_false_on_db_error() -> None:
    vs = _make_vs()
    ctx = _failing_conn(RuntimeError("delete failed"))

    with patch("app.agents.orchestrator.vector_search.asyncpg_connection", ctx):
        result = await vs.remove_agent("agent-123")

    assert result is False
