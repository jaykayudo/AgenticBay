CAPABILITY_DOCUMENT = """
I am a web scraper agent. I fetch public HTTP or HTTPS web pages and return
clean, readable page text plus basic page metadata. I can optionally include
up to 100 resolved links found on the page.

COMMANDS:

1. Scrape a URL
   Request: {"command": "scrape_url", "arguments": {"url": "https://example.com", "include_links": false, "max_chars": 20000}}
   Response: {"data": {"url": "final URL after redirects", "status_code": 200, "title": "page title", "description": "meta description", "text": "clean page text", "text_length": 12345, "returned_text_length": 20000, "truncated": true}}

   Accepted URL schemes: http and https only
   Maximum returned text length: 50,000 characters
   Default returned text length: 20,000 characters
   Optional link extraction: include_links=true returns up to 100 links
   Processing time: usually 2-15 seconds

2. Extract structured data from a URL
   Request: {"command": "extract_structured_data", "arguments": {"url": "https://example.com", "include_links": true, "include_tables": true, "include_json_ld": true}}
   Response: {"data": {"url": "final URL after redirects", "status_code": 200, "title": "page title", "description": "meta description", "headings": [{"level": "h1", "text": "..."}], "open_graph": {"og:title": "..."}, "twitter_card": {"twitter:card": "summary"}, "json_ld": [{"@type": "..."}], "tables": [{"headers": ["..."], "rows": [["..."]]}], "links": [{"url": "...", "text": "..."}]}}

   This command returns machine-readable page structure. It extracts metadata,
   headings, Open Graph tags, Twitter card tags, JSON-LD, HTML tables, links,
   and a short text preview.

PAYMENT:
   I require 0.2 USDC payment before processing any scrape or extraction request.
   When you send the scrape_url or extract_structured_data command, I will respond with a PAYMENT request.
   After the invoice is paid, the orchestrator will send a payment_confirmed
   command and I will process the pending URL request automatically.

PAYMENT CONFIRMATION COMMAND:
   When payment is confirmed, the orchestrator will send:
   {"command": "payment_confirmed", "arguments": {"invoice_id": "..."}}
   I will verify the payment and deliver the scrape result immediately.

ERRORS:
   - Empty URLs will be rejected
   - URLs that do not start with http:// or https:// will be rejected
   - Unsupported content types will be rejected
   - Responses larger than the configured response-size limit will be rejected
   - max_chars must be between 1 and 50,000
   - Unrecognized commands will return an ERROR response
"""
