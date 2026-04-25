import pytest

from src.command_handlers import MAX_DOCUMENT_LENGTH, handle_command
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
async def test_empty_document_returns_error(mgr):
    result = await handle_command("sess-1", "summarize", {"document": "   "}, mgr)

    assert result["type"] == "ERROR"
    assert "empty" in result["data"]["message"].lower()


@pytest.mark.asyncio
async def test_missing_document_key_returns_error(mgr):
    result = await handle_command("sess-1", "summarize", {}, mgr)

    assert result["type"] == "ERROR"


@pytest.mark.asyncio
async def test_oversized_document_returns_error(mgr):
    big_doc = "x" * (MAX_DOCUMENT_LENGTH + 1)
    result = await handle_command("sess-1", "summarize", {"document": big_doc}, mgr)

    assert result["type"] == "ERROR"
    assert "exceeds" in result["data"]["message"].lower()


@pytest.mark.asyncio
async def test_valid_document_without_payment_returns_payment_response(mgr):
    result = await handle_command(
        "sess-1", "summarize", {"document": "Hello world"}, mgr
    )

    assert result["type"] == "PAYMENT"
    assert result["data"]["amount"] == "0.5"
    assert "address" in result["data"]


@pytest.mark.asyncio
async def test_payment_response_stores_pending_document(mgr):
    doc = "Some interesting document content."
    await handle_command("sess-1", "summarize", {"document": doc}, mgr)

    state = mgr.get("sess-1")
    assert state.pending_document == doc
    assert not state.paid


@pytest.mark.asyncio
async def test_valid_document_with_paid_state_returns_job_done(mgr, monkeypatch):
    async def fake_summarize(doc: str) -> str:
        return f"Summary of: {doc[:20]}"

    monkeypatch.setattr("src.command_handlers.summarize_document", fake_summarize)

    state = mgr.get("sess-1")
    state.paid = True

    result = await handle_command(
        "sess-1", "summarize", {"document": "A real document"}, mgr
    )

    assert result["type"] == "JOB_DONE"
    assert "summary" in result["data"]["details"]
    assert result["data"]["details"]["summary"].startswith("Summary of:")
    assert not state.paid


@pytest.mark.asyncio
async def test_payment_confirmed_missing_invoice_id_returns_error(mgr):
    result = await handle_command("sess-1", "payment_confirmed", {}, mgr)

    assert result["type"] == "ERROR"
    assert "invoice_id" in result["data"]["message"].lower()


@pytest.mark.asyncio
async def test_payment_confirmed_without_pending_document_returns_progress(mgr, monkeypatch):
    monkeypatch.setattr("src.command_handlers.verify_invoice_payment", lambda **_: _true())
    result = await handle_command(
        "sess-1", "payment_confirmed", {"invoice_id": "inv-001"}, mgr
    )

    assert result["type"] == "PROGRESS"
    assert mgr.get("sess-1").paid is True


@pytest.mark.asyncio
async def test_payment_confirmed_with_pending_document_returns_job_done(mgr, monkeypatch):
    async def fake_verify(**_):
        return True

    async def fake_summarize(doc: str) -> str:
        return "Fake summary"

    monkeypatch.setattr("src.command_handlers.verify_invoice_payment", fake_verify)
    monkeypatch.setattr("src.command_handlers.summarize_document", fake_summarize)

    state = mgr.get("sess-1")
    state.pending_document = "Pending document text"

    result = await handle_command(
        "sess-1", "payment_confirmed", {"invoice_id": "inv-002"}, mgr
    )

    assert result["type"] == "JOB_DONE"
    assert result["data"]["details"]["summary"] == "Fake summary"
    assert result["data"]["details"]["invoice_id"] == "inv-002"
    # State reset after processing
    assert state.paid is False
    assert state.pending_document is None


@pytest.mark.asyncio
async def test_payment_confirmed_marks_paid_invoice_id(mgr, monkeypatch):
    monkeypatch.setattr("src.command_handlers.verify_invoice_payment", lambda **_: _true())
    await handle_command(
        "sess-1", "payment_confirmed", {"invoice_id": "inv-xyz"}, mgr
    )

    # Even after reset, the invoice id is recorded (mark_paid was called)
    # We check via the paid_invoice_ids list before state is reset
    # (payment_confirmed without pending doc does NOT reset paid)
    state = mgr.get("sess-1")
    assert "inv-xyz" in state.paid_invoice_ids


# Helper — returns True as a coroutine for monkeypatching
async def _true(**_):
    return True
