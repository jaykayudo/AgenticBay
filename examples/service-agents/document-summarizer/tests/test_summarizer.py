from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.summarizer import summarize_document


@pytest.mark.asyncio
async def test_summarize_document_returns_text_from_claude():
    mock_message = MagicMock()
    mock_message.content = [MagicMock(text="A clear and concise summary.")]

    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(return_value=mock_message)

    with patch("src.summarizer._get_client", return_value=mock_client):
        result = await summarize_document("This is a test document.")

    assert result == "A clear and concise summary."


@pytest.mark.asyncio
async def test_summarize_document_passes_correct_model_and_system_prompt():
    mock_message = MagicMock()
    mock_message.content = [MagicMock(text="Summary")]

    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(return_value=mock_message)

    with patch("src.summarizer._get_client", return_value=mock_client):
        await summarize_document("Sample text")

    call_kwargs = mock_client.messages.create.call_args.kwargs
    assert call_kwargs["model"] == "claude-sonnet-4-6"
    assert call_kwargs["max_tokens"] == 4000
    assert "summarizer" in call_kwargs["system"].lower()


@pytest.mark.asyncio
async def test_summarize_document_includes_document_in_user_message():
    mock_message = MagicMock()
    mock_message.content = [MagicMock(text="Summary")]

    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(return_value=mock_message)

    doc = "A very specific piece of content to summarize."
    with patch("src.summarizer._get_client", return_value=mock_client):
        await summarize_document(doc)

    messages = mock_client.messages.create.call_args.kwargs["messages"]
    assert any(doc in str(m["content"]) for m in messages)


@pytest.mark.asyncio
async def test_summarize_document_propagates_anthropic_exception():
    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(side_effect=RuntimeError("API error"))

    with patch("src.summarizer._get_client", return_value=mock_client):
        with pytest.raises(RuntimeError, match="API error"):
            await summarize_document("Anything")
