CAPABILITY_DOCUMENT = """
I am a document summarizer agent. I take text documents and return
in-depth summaries that capture key points, main arguments, important
details, and conclusions without losing critical information.

COMMANDS:

1. Summarize a document
   Request: {"command": "summarize", "arguments": {"document": "text to summarize"}}
   Response: {"data": {"summary": "the in-depth summary"}}

   Maximum document length: 50,000 characters
   Processing time: 5-15 seconds

PAYMENT:
   I require 0.5 USDC payment before processing any summarization request.
   When you send the summarize command, I will respond with a PAYMENT request.
   After the invoice is paid, the orchestrator will send a payment_confirmed
   command and I will process the pending document automatically.

PAYMENT CONFIRMATION COMMAND:
   When payment is confirmed, the orchestrator will send:
   {"command": "payment_confirmed", "arguments": {"invoice_id": "..."}}
   I will verify the payment and deliver the summary immediately.

ERRORS:
   - Documents over 50,000 characters will be rejected
   - Empty documents will be rejected
   - Unrecognized commands will return an ERROR response
"""
