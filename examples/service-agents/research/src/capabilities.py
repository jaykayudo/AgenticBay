CAPABILITY_DOCUMENT = """
I am an AI research agent. I research a topic using optional supplied source
URLs and produce a structured research report with summary, key findings,
source notes, risks and limitations, and follow-up questions.

COMMANDS:

1. Research a topic
   Request: {"command": "research_topic", "arguments": {"topic": "research question", "sources": ["https://example.com/source"], "depth": "standard", "max_sources": 5}}
   Response: {"data": {"topic": "research question", "depth": "standard", "sources_fetched": [{"url": "...", "title": "...", "error": ""}], "report": "JSON research report"}}

   Maximum topic length: 500 characters
   Accepted depths: brief, standard, deep
   Maximum supplied sources: 8
   Processing time: usually 10-45 seconds depending on source count

PAYMENT:
   I require 1.0 USDC payment before processing any research request.
   When you send the research_topic command, I will respond with a PAYMENT request.
   After the invoice is paid, the orchestrator will send a payment_confirmed
   command and I will process the pending research request automatically.

PAYMENT CONFIRMATION COMMAND:
   When payment is confirmed, the orchestrator will send:
   {"command": "payment_confirmed", "arguments": {"invoice_id": "..."}}
   I will verify the payment and deliver the research report immediately.

ERRORS:
   - Empty topics will be rejected
   - Topics over 500 characters will be rejected
   - Source URLs must start with http:// or https://
   - depth must be brief, standard, or deep
   - Unrecognized commands will return an ERROR response
"""
