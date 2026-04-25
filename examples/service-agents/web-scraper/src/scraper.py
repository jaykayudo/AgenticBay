from __future__ import annotations

import logging
import json
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from .config import settings

logger = logging.getLogger(__name__)

DEFAULT_MAX_CHARS = 20_000
MAX_TEXT_CHARS = 50_000
MAX_LINKS = 100
MAX_TABLE_ROWS = 50


class ScraperError(ValueError):
    """Raised for expected scraping failures that should be shown to callers."""


def validate_url(url: str) -> str:
    candidate = (url or "").strip()
    parsed = urlparse(candidate)

    if parsed.scheme not in {"http", "https"}:
        raise ScraperError("URL must start with http:// or https://")

    if not parsed.netloc:
        raise ScraperError("URL must include a host")

    return candidate


def _extract_metadata(soup: BeautifulSoup) -> dict[str, str]:
    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    description = ""

    description_tag = soup.find("meta", attrs={"name": "description"})
    if description_tag and description_tag.get("content"):
        description = str(description_tag["content"]).strip()

    return {"title": title, "description": description}


def _extract_meta_properties(soup: BeautifulSoup, prefix: str) -> dict[str, str]:
    values: dict[str, str] = {}

    for tag in soup.find_all("meta"):
        key = tag.get("property") or tag.get("name")
        content = tag.get("content")
        if not key or not content:
            continue

        key = str(key)
        if key.startswith(prefix):
            values[key] = str(content).strip()

    return values


def _extract_links(soup: BeautifulSoup, base_url: str) -> list[dict[str, str]]:
    links: list[dict[str, str]] = []
    seen: set[str] = set()

    for anchor in soup.find_all("a", href=True):
        href = urljoin(base_url, str(anchor["href"]).strip())
        parsed = urlparse(href)
        if parsed.scheme not in {"http", "https"} or href in seen:
            continue

        seen.add(href)
        links.append(
            {
                "url": href,
                "text": anchor.get_text(" ", strip=True)[:200],
            }
        )

        if len(links) >= MAX_LINKS:
            break

    return links


def _extract_headings(soup: BeautifulSoup) -> list[dict[str, str]]:
    headings: list[dict[str, str]] = []

    for tag in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]):
        text = tag.get_text(" ", strip=True)
        if text:
            headings.append({"level": tag.name, "text": text})

    return headings


def _extract_json_ld(soup: BeautifulSoup) -> list[dict]:
    items: list[dict] = []

    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        raw = script.string or script.get_text("", strip=True)
        if not raw:
            continue

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            continue

        if isinstance(parsed, list):
            items.extend(item for item in parsed if isinstance(item, dict))
        elif isinstance(parsed, dict):
            items.append(parsed)

    return items


def _extract_tables(soup: BeautifulSoup) -> list[dict]:
    tables: list[dict] = []

    for table in soup.find_all("table"):
        headers = [
            cell.get_text(" ", strip=True)
            for cell in table.find_all("th")
            if cell.get_text(" ", strip=True)
        ]
        rows: list[list[str]] = []

        for row in table.find_all("tr"):
            cells = [
                cell.get_text(" ", strip=True)
                for cell in row.find_all(["td", "th"])
                if cell.get_text(" ", strip=True)
            ]
            if cells:
                rows.append(cells)

            if len(rows) >= MAX_TABLE_ROWS:
                break

        if rows:
            tables.append(
                {
                    "headers": headers,
                    "rows": rows,
                    "row_count_returned": len(rows),
                }
            )

    return tables


def _extract_text(html: str) -> tuple[str, BeautifulSoup]:
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(["script", "style", "noscript", "template", "svg"]):
        tag.decompose()

    text = soup.get_text("\n", strip=True)
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return "\n".join(lines), soup


async def _fetch_page(url: str) -> httpx.Response:
    target_url = validate_url(url)
    logger.info("Fetching URL: %s", target_url)

    headers = {
        "User-Agent": (
            "AgenticBayWebScraper/1.0 "
            "(compatible; service-agent; +https://agentic.bay)"
        )
    }

    try:
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=settings.SCRAPER_TIMEOUT_SECONDS,
            headers=headers,
        ) as client:
            response = await client.get(target_url)
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise ScraperError(
            f"Page returned HTTP {exc.response.status_code}"
        ) from exc
    except httpx.RequestError as exc:
        raise ScraperError(f"Could not fetch URL: {exc}") from exc

    content_type = response.headers.get("content-type", "")
    if "text/html" not in content_type and "text/plain" not in content_type:
        raise ScraperError(f"Unsupported content type: {content_type or 'unknown'}")

    if len(response.content) > settings.SCRAPER_MAX_RESPONSE_BYTES:
        raise ScraperError("Response is too large to scrape")

    return response

async def scrape_url(
    url: str,
    include_links: bool = False,
    max_chars: int | None = None,
) -> dict:
    """Fetch a public web page and return readable text and metadata."""
    char_limit = max_chars or DEFAULT_MAX_CHARS

    if char_limit < 1 or char_limit > MAX_TEXT_CHARS:
        raise ScraperError(f"max_chars must be between 1 and {MAX_TEXT_CHARS}")

    response = await _fetch_page(url)
    html = response.text
    text, soup = _extract_text(html)
    metadata = _extract_metadata(soup)
    truncated = len(text) > char_limit
    visible_text = text[:char_limit]

    result = {
        "url": str(response.url),
        "status_code": response.status_code,
        "title": metadata["title"],
        "description": metadata["description"],
        "text": visible_text,
        "text_length": len(text),
        "returned_text_length": len(visible_text),
        "truncated": truncated,
    }

    if include_links:
        result["links"] = _extract_links(soup, str(response.url))

    return result


async def extract_structured_data(
    url: str,
    include_links: bool = True,
    include_tables: bool = True,
    include_json_ld: bool = True,
) -> dict:
    """Fetch a public web page and return structured page data."""
    response = await _fetch_page(url)
    soup = BeautifulSoup(response.text, "html.parser")
    text, _ = _extract_text(response.text)
    metadata = _extract_metadata(soup)

    result = {
        "url": str(response.url),
        "status_code": response.status_code,
        "title": metadata["title"],
        "description": metadata["description"],
        "headings": _extract_headings(soup),
        "open_graph": _extract_meta_properties(soup, "og:"),
        "twitter_card": _extract_meta_properties(soup, "twitter:"),
        "text_preview": text[:1000],
        "text_length": len(text),
    }

    if include_json_ld:
        result["json_ld"] = _extract_json_ld(soup)

    if include_tables:
        result["tables"] = _extract_tables(soup)

    if include_links:
        result["links"] = _extract_links(soup, str(response.url))

    return result
