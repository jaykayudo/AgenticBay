from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.scraper import ScraperError, extract_structured_data, scrape_url, validate_url


def test_validate_url_accepts_http_and_https():
    assert validate_url("https://example.com") == "https://example.com"
    assert validate_url("http://example.com/page") == "http://example.com/page"


def test_validate_url_rejects_unsupported_scheme():
    with pytest.raises(ScraperError, match="http:// or https://"):
        validate_url("ftp://example.com")


@pytest.mark.asyncio
async def test_scrape_url_extracts_text_metadata_and_links():
    html = """
    <html>
      <head>
        <title>Example Page</title>
        <meta name="description" content="A useful test page">
      </head>
      <body>
        <script>ignore()</script>
        <h1>Hello</h1>
        <p>Readable content.</p>
        <a href="/next">Next page</a>
      </body>
    </html>
    """
    response = MagicMock()
    response.status_code = 200
    response.url = "https://example.com/source"
    response.headers = {"content-type": "text/html; charset=utf-8"}
    response.content = html.encode()
    response.text = html
    response.raise_for_status = MagicMock()

    client = AsyncMock()
    client.get = AsyncMock(return_value=response)
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)

    with patch("src.scraper.httpx.AsyncClient", return_value=client):
        result = await scrape_url(
            "https://example.com/source",
            include_links=True,
            max_chars=1000,
        )

    assert result["title"] == "Example Page"
    assert result["description"] == "A useful test page"
    assert "Readable content." in result["text"]
    assert "ignore()" not in result["text"]
    assert result["links"][0]["url"] == "https://example.com/next"


@pytest.mark.asyncio
async def test_scrape_url_truncates_text():
    html = "<html><body><p>abcdefghij</p></body></html>"
    response = MagicMock()
    response.status_code = 200
    response.url = "https://example.com"
    response.headers = {"content-type": "text/html"}
    response.content = html.encode()
    response.text = html
    response.raise_for_status = MagicMock()

    client = AsyncMock()
    client.get = AsyncMock(return_value=response)
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)

    with patch("src.scraper.httpx.AsyncClient", return_value=client):
        result = await scrape_url("https://example.com", max_chars=4)

    assert result["text"] == "abcd"
    assert result["truncated"] is True


@pytest.mark.asyncio
async def test_extract_structured_data_returns_machine_readable_page_data():
    html = """
    <html>
      <head>
        <title>Product Page</title>
        <meta name="description" content="A product page">
        <meta property="og:title" content="Open Graph Product">
        <meta name="twitter:card" content="summary">
        <script type="application/ld+json">
          {"@type": "Product", "name": "Test Product"}
        </script>
      </head>
      <body>
        <h1>Test Product</h1>
        <h2>Specs</h2>
        <table>
          <tr><th>Name</th><th>Value</th></tr>
          <tr><td>Weight</td><td>1kg</td></tr>
        </table>
        <a href="/buy">Buy now</a>
      </body>
    </html>
    """
    response = MagicMock()
    response.status_code = 200
    response.url = "https://example.com/product"
    response.headers = {"content-type": "text/html; charset=utf-8"}
    response.content = html.encode()
    response.text = html
    response.raise_for_status = MagicMock()

    client = AsyncMock()
    client.get = AsyncMock(return_value=response)
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)

    with patch("src.scraper.httpx.AsyncClient", return_value=client):
        result = await extract_structured_data("https://example.com/product")

    assert result["title"] == "Product Page"
    assert result["open_graph"]["og:title"] == "Open Graph Product"
    assert result["twitter_card"]["twitter:card"] == "summary"
    assert result["json_ld"][0]["name"] == "Test Product"
    assert result["headings"][0] == {"level": "h1", "text": "Test Product"}
    assert result["tables"][0]["rows"][1] == ["Weight", "1kg"]
    assert result["links"][0]["url"] == "https://example.com/buy"
