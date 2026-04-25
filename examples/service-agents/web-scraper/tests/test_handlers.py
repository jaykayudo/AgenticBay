import pytest

from src.command_handlers import SCRAPE_PRICE, handle_command
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
async def test_empty_url_returns_error(mgr):
    result = await handle_command("sess-1", "scrape_url", {"url": "   "}, mgr)

    assert result["type"] == "ERROR"
    assert "url" in result["data"]["message"].lower()


@pytest.mark.asyncio
async def test_invalid_url_scheme_returns_error(mgr):
    result = await handle_command("sess-1", "scrape_url", {"url": "ftp://x.test"}, mgr)

    assert result["type"] == "ERROR"
    assert "http" in result["data"]["message"].lower()


@pytest.mark.asyncio
async def test_invalid_max_chars_returns_error(mgr):
    result = await handle_command(
        "sess-1",
        "scrape_url",
        {"url": "https://example.com", "max_chars": 0},
        mgr,
    )

    assert result["type"] == "ERROR"
    assert "max_chars" in result["data"]["message"]


@pytest.mark.asyncio
async def test_valid_url_without_payment_returns_payment_response(mgr):
    result = await handle_command(
        "sess-1",
        "scrape_url",
        {"url": "https://example.com"},
        mgr,
    )

    assert result["type"] == "PAYMENT"
    assert result["data"]["amount"] == SCRAPE_PRICE
    assert "address" in result["data"]


@pytest.mark.asyncio
async def test_payment_response_stores_pending_scrape(mgr):
    await handle_command(
        "sess-1",
        "scrape_url",
        {"url": "https://example.com", "include_links": True},
        mgr,
    )

    state = mgr.get("sess-1")
    assert state.pending_scrape["url"] == "https://example.com"
    assert state.pending_scrape["operation"] == "scrape_url"
    assert state.pending_scrape["include_links"] is True
    assert not state.paid


@pytest.mark.asyncio
async def test_extract_structured_data_without_payment_returns_payment_response(mgr):
    result = await handle_command(
        "sess-1",
        "extract_structured_data",
        {"url": "https://example.com"},
        mgr,
    )

    assert result["type"] == "PAYMENT"
    assert result["data"]["amount"] == SCRAPE_PRICE
    assert mgr.get("sess-1").pending_scrape["operation"] == "extract_structured_data"


@pytest.mark.asyncio
async def test_valid_url_with_paid_state_returns_job_done(mgr, monkeypatch):
    async def fake_scrape_url(**_):
        return {"url": "https://example.com", "text": "Scraped text"}

    monkeypatch.setattr("src.command_handlers.scrape_url", fake_scrape_url)

    state = mgr.get("sess-1")
    state.paid = True

    result = await handle_command(
        "sess-1",
        "scrape_url",
        {"url": "https://example.com"},
        mgr,
    )

    assert result["type"] == "JOB_DONE"
    assert result["data"]["details"]["text"] == "Scraped text"
    assert not state.paid


@pytest.mark.asyncio
async def test_extract_structured_data_with_paid_state_returns_job_done(mgr, monkeypatch):
    async def fake_extract_structured_data(**_):
        return {"url": "https://example.com", "headings": [{"level": "h1", "text": "Hi"}]}

    monkeypatch.setattr(
        "src.command_handlers.extract_structured_data",
        fake_extract_structured_data,
    )

    state = mgr.get("sess-1")
    state.paid = True

    result = await handle_command(
        "sess-1",
        "extract_structured_data",
        {"url": "https://example.com"},
        mgr,
    )

    assert result["type"] == "JOB_DONE"
    assert result["data"]["details"]["headings"][0]["text"] == "Hi"
    assert not state.paid


@pytest.mark.asyncio
async def test_payment_confirmed_missing_invoice_id_returns_error(mgr):
    result = await handle_command("sess-1", "payment_confirmed", {}, mgr)

    assert result["type"] == "ERROR"
    assert "invoice_id" in result["data"]["message"].lower()


@pytest.mark.asyncio
async def test_payment_confirmed_without_pending_scrape_returns_progress(
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
async def test_payment_confirmed_with_pending_scrape_returns_job_done(
    mgr, monkeypatch
):
    async def fake_verify(**_):
        return True

    async def fake_scrape_url(**_):
        return {"url": "https://example.com", "text": "Fake scrape"}

    monkeypatch.setattr("src.command_handlers.verify_invoice_payment", fake_verify)
    monkeypatch.setattr("src.command_handlers.scrape_url", fake_scrape_url)

    state = mgr.get("sess-1")
    state.pending_scrape = {
        "operation": "scrape_url",
        "url": "https://example.com",
        "include_links": False,
    }

    result = await handle_command(
        "sess-1", "payment_confirmed", {"invoice_id": "inv-002"}, mgr
    )

    assert result["type"] == "JOB_DONE"
    assert result["data"]["details"]["text"] == "Fake scrape"
    assert result["data"]["details"]["invoice_id"] == "inv-002"
    assert state.paid is False
    assert state.pending_scrape is None


@pytest.mark.asyncio
async def test_payment_confirmed_with_pending_structured_request_returns_job_done(
    mgr, monkeypatch
):
    async def fake_verify(**_):
        return True

    async def fake_extract_structured_data(**_):
        return {"url": "https://example.com", "json_ld": [{"name": "Thing"}]}

    monkeypatch.setattr("src.command_handlers.verify_invoice_payment", fake_verify)
    monkeypatch.setattr(
        "src.command_handlers.extract_structured_data",
        fake_extract_structured_data,
    )

    state = mgr.get("sess-1")
    state.pending_scrape = {
        "operation": "extract_structured_data",
        "url": "https://example.com",
    }

    result = await handle_command(
        "sess-1", "payment_confirmed", {"invoice_id": "inv-structured"}, mgr
    )

    assert result["type"] == "JOB_DONE"
    assert result["data"]["details"]["json_ld"][0]["name"] == "Thing"
    assert result["data"]["details"]["invoice_id"] == "inv-structured"
    assert state.paid is False
    assert state.pending_scrape is None


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
