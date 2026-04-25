from __future__ import annotations

import logging
from urllib.parse import urlparse

import httpx
from anthropic import AsyncAnthropic
from bs4 import BeautifulSoup

from .config import settings

logger = logging.getLogger(__name__)

_client: AsyncAnthropic | None = None

MAX_TOPIC_LENGTH = 500
MAX_SOURCES = 8
MAX_SOURCE_CHARS = 12_000
VALID_DEPTHS = {"brief", "standard", "deep"}

RESEARCH_SYSTEM_PROMPT = """
You are an expert research analyst. Produce careful, useful research reports.

Requirements:
1. Separate sourced findings from inference.
2. Cite source numbers when using supplied source material.
3. State uncertainty and limitations.
4. Avoid inventing citations, dates, statistics, or claims.
5. Include practical next steps or follow-up questions.

Return a concise JSON object with these keys:
summary, key_findings, source_notes, risks_and_limitations, follow_up_questions.
"""


class ResearchError(ValueError):
    """Raised for expected research failures that should be shown to callers."""


def _get_client() -> AsyncAnthropic:
    global _client
    if _client is None:
        _client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
    return _client


def validate_research_request(
    topic: str,
    sources: list[str] | None = None,
    depth: str = "standard",
    max_sources: int = 5,
) -> dict:
    clean_topic = (topic or "").strip()
    if not clean_topic:
        raise ResearchError("Topic cannot be empty")

    if len(clean_topic) > MAX_TOPIC_LENGTH:
        raise ResearchError(f"Topic exceeds maximum length of {MAX_TOPIC_LENGTH} characters")

    if depth not in VALID_DEPTHS:
        raise ResearchError("depth must be one of: brief, standard, deep")

    if max_sources < 0 or max_sources > MAX_SOURCES:
        raise ResearchError(f"max_sources must be between 0 and {MAX_SOURCES}")

    clean_sources = []
    for source in (sources or [])[:max_sources]:
        clean_source = str(source).strip()
        parsed = urlparse(clean_source)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ResearchError("All sources must be valid http:// or https:// URLs")
        clean_sources.append(clean_source)

    return {
        "topic": clean_topic,
        "sources": clean_sources,
        "depth": depth,
        "max_sources": max_sources,
    }


async def _fetch_source(url: str) -> dict:
    logger.info("Fetching research source: %s", url)
    headers = {
        "User-Agent": (
            "AgenticBayResearchAgent/1.0 "
            "(compatible; service-agent; +https://agentic.bay)"
        )
    }

    try:
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=settings.RESEARCH_TIMEOUT_SECONDS,
            headers=headers,
        ) as client:
            response = await client.get(url)
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        return {
            "url": url,
            "error": f"HTTP {exc.response.status_code}",
        }
    except httpx.RequestError as exc:
        return {
            "url": url,
            "error": f"Could not fetch source: {exc}",
        }

    content_type = response.headers.get("content-type", "")
    if "text/html" not in content_type and "text/plain" not in content_type:
        return {
            "url": url,
            "error": f"Unsupported content type: {content_type or 'unknown'}",
        }

    soup = BeautifulSoup(response.text, "html.parser")
    for tag in soup(["script", "style", "noscript", "template", "svg"]):
        tag.decompose()

    title = soup.title.get_text(" ", strip=True) if soup.title else str(response.url)
    text = soup.get_text("\n", strip=True)
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    return {
        "url": str(response.url),
        "title": title,
        "text": "\n".join(lines)[:MAX_SOURCE_CHARS],
    }


def _build_user_prompt(topic: str, depth: str, sources: list[dict]) -> str:
    source_blocks = []
    for index, source in enumerate(sources, start=1):
        if source.get("error"):
            source_blocks.append(
                f"[Source {index}]\nURL: {source['url']}\nERROR: {source['error']}"
            )
            continue

        source_blocks.append(
            "\n".join(
                [
                    f"[Source {index}]",
                    f"Title: {source['title']}",
                    f"URL: {source['url']}",
                    "Content:",
                    source["text"],
                ]
            )
        )

    source_text = "\n\n---\n\n".join(source_blocks) or "No external sources provided."

    return f"""
Research topic: {topic}
Depth: {depth}

Source material:
{source_text}

Create the requested JSON research report. If no usable sources are provided,
make that limitation explicit and keep claims conservative.
"""


async def run_research(
    topic: str,
    sources: list[str] | None = None,
    depth: str = "standard",
    max_sources: int = 5,
) -> dict:
    """Research a topic using optional supplied URLs and Claude synthesis."""
    request = validate_research_request(topic, sources, depth, max_sources)
    fetched_sources = [
        await _fetch_source(source_url) for source_url in request["sources"]
    ]

    max_tokens = {"brief": 1200, "standard": 2500, "deep": 4000}[request["depth"]]
    message = await _get_client().messages.create(
        model="claude-sonnet-4-6",
        max_tokens=max_tokens,
        system=RESEARCH_SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": _build_user_prompt(
                    request["topic"],
                    request["depth"],
                    fetched_sources,
                ),
            }
        ],
    )

    report = message.content[0].text  # type: ignore[union-attr]
    return {
        "topic": request["topic"],
        "depth": request["depth"],
        "sources_requested": len(request["sources"]),
        "sources_fetched": [
            {
                "url": source["url"],
                "title": source.get("title", ""),
                "error": source.get("error", ""),
            }
            for source in fetched_sources
        ],
        "report": report,
    }
