CAPABILITY_DOCUMENT = """
I am a research agent. I turn a topic and optional source notes into a
structured research brief that is useful for product decisions, market
exploration, and technical scoping.

COMMANDS:

1. Research a topic
   Request: {"command": "research", "arguments": {"topic": "text", "context": "optional notes", "focus_areas": ["..."]}}
   Response: {"data": {"brief": "the research brief"}}

   Recommended inputs:
   - topic: required
   - context: optional supporting notes, links, or source material
   - focus_areas: optional list of angles to emphasize

   Processing time: 5-20 seconds depending on topic length

PAYMENT:
   I require 0.01 USDC payment before processing any research request.
   When you send the research command, I will respond with a PAYMENT request.
   After the invoice is paid, the orchestrator will send payment_confirmed
   and I will process the pending topic automatically.

PAYMENT CONFIRMATION COMMAND:
   When payment is confirmed, the orchestrator will send:
   {"command": "payment_confirmed", "arguments": {"invoice_id": "..."}}
   I will verify the payment and deliver the brief immediately.

OUTPUT:
   The research brief includes:
   - executive summary
   - key findings
   - assumptions and caveats
   - open questions
   - recommended next steps

ERRORS:
   - Empty topics will be rejected
   - Extremely large context payloads may be rejected
   - Unrecognized commands will return an ERROR response
"""
