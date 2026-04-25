import pytest

from src.command_handlers import RESEARCH_PRICE, handle_command
from src.session_manager import SessionManager


@pytest.fixture()
def mgr():
    m = SessionManager()
    m.create("sess-1")
    return m


@pytest.mark.asyncio
async def test_unknown_command_returns_error(mgr):
    result = await handle_command("sess-1", "do_magic", {}, mgr)

    assert result["type"] == "ERROR"
    assert "Unknown command" in result["data"]["message"]


@pytest.mark.asyncio
async def test_empty_topic_returns_error(mgr):
    result = await handle_command("sess-1", "research_topic", {"topic": "   "}, mgr)

    assert result["type"] == "ERROR"
    assert "topic" in result["data"]["message"].lower()


@pytest.mark.asyncio
async def test_sources_must_be_list(mgr):
    result = await handle_command(
        "sess-1",
        "research_topic",
        {"topic": "AI", "sources": "https://example.com"},
        mgr,
    )

    assert result["type"] == "ERROR"
    assert "sources" in result["data"]["message"]


@pytest.mark.asyncio
async def test_valid_topic_without_payment_returns_payment_response(mgr):
    result = await handle_command(
        "sess-1",
        "research_topic",
        {"topic": "Stablecoin payments"},
        mgr,
    )

    assert result["type"] == "PAYMENT"
    assert result["data"]["amount"] == RESEARCH_PRICE
    assert "address" in result["data"]


@pytest.mark.asyncio
async def test_payment_response_stores_pending_research(mgr):
    await handle_command(
        "sess-1",
        "research_topic",
        {"topic": "Stablecoin payments", "depth": "brief"},
        mgr,
    )

    state = mgr.get("sess-1")
    assert state.pending_research["topic"] == "Stablecoin payments"
    assert state.pending_research["depth"] == "brief"
    assert not state.paid


@pytest.mark.asyncio
async def test_valid_topic_with_paid_state_returns_job_done(mgr, monkeypatch):
    async def fake_run_research(**_):
        return {"topic": "AI", "report": '{"summary":"Done"}'}

    monkeypatch.setattr("src.command_handlers.run_research", fake_run_research)

    state = mgr.get("sess-1")
    state.paid = True

    result = await handle_command("sess-1", "research_topic", {"topic": "AI"}, mgr)

    assert result["type"] == "JOB_DONE"
    assert result["data"]["details"]["report"] == '{"summary":"Done"}'
    assert not state.paid


@pytest.mark.asyncio
async def test_payment_confirmed_missing_invoice_id_returns_error(mgr):
    result = await handle_command("sess-1", "payment_confirmed", {}, mgr)

    assert result["type"] == "ERROR"
    assert "invoice_id" in result["data"]["message"].lower()


@pytest.mark.asyncio
async def test_payment_confirmed_without_pending_research_returns_progress(
    mgr, monkeypatch
):
    monkeypatch.setattr(
        "src.command_handlers.verify_invoice_payment", lambda **_: _true()
    )
    result = await handle_command(
        "sess-1", "payment_confirmed", {"invoice_id": "inv-001"}, mgr
    )

    assert result["type"] == "PROGRESS"
    assert mgr.get("sess-1").paid is True


@pytest.mark.asyncio
async def test_payment_confirmed_with_pending_research_returns_job_done(
    mgr, monkeypatch
):
    async def fake_verify(**_):
        return True

    async def fake_run_research(**_):
        return {"topic": "AI", "report": '{"summary":"Paid"}'}

    monkeypatch.setattr("src.command_handlers.verify_invoice_payment", fake_verify)
    monkeypatch.setattr("src.command_handlers.run_research", fake_run_research)

    state = mgr.get("sess-1")
    state.pending_research = {"topic": "AI", "sources": [], "depth": "standard", "max_sources": 5}

    result = await handle_command(
        "sess-1", "payment_confirmed", {"invoice_id": "inv-002"}, mgr
    )

    assert result["type"] == "JOB_DONE"
    assert result["data"]["details"]["report"] == '{"summary":"Paid"}'
    assert result["data"]["details"]["invoice_id"] == "inv-002"
    assert state.paid is False
    assert state.pending_research is None


@pytest.mark.asyncio
async def test_payment_confirmed_marks_paid_invoice_id(mgr, monkeypatch):
    monkeypatch.setattr(
        "src.command_handlers.verify_invoice_payment", lambda **_: _true()
    )
    await handle_command("sess-1", "payment_confirmed", {"invoice_id": "inv-xyz"}, mgr)

    state = mgr.get("sess-1")
    assert "inv-xyz" in state.paid_invoice_ids


async def _true(**_):
    return True
