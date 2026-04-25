from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.researcher import ResearchError, run_research, validate_research_request


def test_validate_research_request_accepts_valid_input():
    result = validate_research_request(
        "Stablecoin payments",
        ["https://example.com/source"],
        "standard",
        5,
    )

    assert result["topic"] == "Stablecoin payments"
    assert result["sources"] == ["https://example.com/source"]


def test_validate_research_request_rejects_empty_topic():
    with pytest.raises(ResearchError, match="Topic cannot be empty"):
        validate_research_request("", [], "standard", 5)


def test_validate_research_request_rejects_invalid_source():
    with pytest.raises(ResearchError, match="valid http:// or https://"):
        validate_research_request("Topic", ["ftp://example.com"], "standard", 5)


def test_validate_research_request_rejects_invalid_depth():
    with pytest.raises(ResearchError, match="depth"):
        validate_research_request("Topic", [], "extreme", 5)


@pytest.mark.asyncio
async def test_run_research_fetches_sources_and_calls_claude():
    html = """
    <html>
      <head><title>Source Page</title></head>
      <body><script>ignore()</script><h1>Finding</h1><p>Useful evidence.</p></body>
    </html>
    """
    response = MagicMock()
    response.status_code = 200
    response.url = "https://example.com/source"
    response.headers = {"content-type": "text/html"}
    response.text = html
    response.raise_for_status = MagicMock()

    http_client = AsyncMock()
    http_client.get = AsyncMock(return_value=response)
    http_client.__aenter__ = AsyncMock(return_value=http_client)
    http_client.__aexit__ = AsyncMock(return_value=None)

    mock_message = MagicMock()
    mock_message.content = [MagicMock(text='{"summary":"Good report"}')]

    llm_client = AsyncMock()
    llm_client.messages.create = AsyncMock(return_value=mock_message)

    with patch("src.researcher.httpx.AsyncClient", return_value=http_client):
        with patch("src.researcher._get_client", return_value=llm_client):
            result = await run_research(
                "Stablecoin payments",
                ["https://example.com/source"],
                "brief",
                5,
            )

    assert result["topic"] == "Stablecoin payments"
    assert result["sources_fetched"][0]["title"] == "Source Page"
    assert result["report"] == '{"summary":"Good report"}'

    prompt = llm_client.messages.create.call_args.kwargs["messages"][0]["content"]
    assert "Useful evidence." in prompt
    assert "ignore()" not in prompt
