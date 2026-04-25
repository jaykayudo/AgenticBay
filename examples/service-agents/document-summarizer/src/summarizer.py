from __future__ import annotations

import logging

from anthropic import AsyncAnthropic

from .config import settings

logger = logging.getLogger(__name__)

_client: AsyncAnthropic | None = None

SUMMARIZATION_SYSTEM_PROMPT = """
You are an expert document summarizer. Your job is to produce
in-depth summaries that:

1. Capture all key points and main arguments
2. Preserve important details, statistics, and specific claims
3. Maintain the original document's tone and perspective
4. Structure the summary clearly with appropriate sections
5. Include conclusions and implications
6. Be comprehensive but not redundant

The summary should be thorough enough that a reader could understand
the document's full value without reading the original.

Return ONLY the summary. No preamble, no meta-commentary.
"""


def _get_client() -> AsyncAnthropic:
    global _client
    if _client is None:
        _client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
    return _client


async def summarize_document(document: str) -> str:
    """Generate an in-depth summary using Claude."""
    logger.info("Summarizing document of length %d", len(document))

    message = await _get_client().messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4000,
        system=SUMMARIZATION_SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": f"Please provide an in-depth summary of this document:\n\n{document}",
            }
        ],
    )

    summary = message.content[0].text  # type: ignore[union-attr]
    logger.info("Generated summary of length %d", len(summary))
    return summary
