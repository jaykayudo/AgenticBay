from __future__ import annotations

import logging
from typing import Any

from .config import settings
from .payment_verifier import verify_invoice_payment
from .session_manager import SessionManager
from .summarizer import summarize_document

logger = logging.getLogger(__name__)

SUMMARIZATION_PRICE = "0.5"
MAX_DOCUMENT_LENGTH = 50_000


async def handle_command(
    session_id: str,
    command: str,
    arguments: dict[str, Any],
    session_manager: SessionManager,
) -> dict[str, Any] | None:
    """Main command router."""
    handlers = {
        "summarize": _handle_summarize,
        "payment_confirmed": _handle_payment_confirmed,
    }

    handler = handlers.get(command)
    if handler is None:
        return {"type": "ERROR", "data": {"message": f"Unknown command: {command}"}}

    return await handler(session_id, arguments, session_manager)


async def _handle_summarize(
    session_id: str,
    arguments: dict[str, Any],
    session_manager: SessionManager,
) -> dict[str, Any]:
    document = arguments.get("document", "")

    if not document or not document.strip():
        return {"type": "ERROR", "data": {"message": "Document cannot be empty"}}

    if len(document) > MAX_DOCUMENT_LENGTH:
        return {
            "type": "ERROR",
            "data": {
                "message": (
                    f"Document exceeds maximum length of {MAX_DOCUMENT_LENGTH} characters"
                )
            },
        }

    state = session_manager.get(session_id)
    if state is None:
        return {"type": "ERROR", "data": {"message": "Session not found"}}

    if not state.paid:
        state.pending_document = document
        return {
            "type": "PAYMENT",
            "data": {
                "amount": SUMMARIZATION_PRICE,
                "address": settings.AGENT_WALLET_ADDRESS,
                "description": "Payment for document summarization (0.5 USDC)",
            },
        }

    # Already paid — process immediately
    summary = await summarize_document(document)
    state.paid = False
    state.pending_document = None

    return {
        "type": "JOB_DONE",
        "data": {
            "message": "Document summarized successfully",
            "details": {
                "summary": summary,
                "original_length": len(document),
                "summary_length": len(summary),
            },
        },
    }


async def _handle_payment_confirmed(
    session_id: str,
    arguments: dict[str, Any],
    session_manager: SessionManager,
) -> dict[str, Any]:
    invoice_id = arguments.get("invoice_id")
    if not invoice_id:
        return {"type": "ERROR", "data": {"message": "Missing invoice_id"}}

    state = session_manager.get(session_id)
    if state is None:
        return {"type": "ERROR", "data": {"message": "Session not found"}}

    verified = await verify_invoice_payment(
        wallet_address=settings.AGENT_WALLET_ADDRESS,
        expected_amount=float(SUMMARIZATION_PRICE),
    )
    if not verified:
        return {"type": "ERROR", "data": {"message": "Payment verification failed"}}

    session_manager.mark_paid(session_id, invoice_id)

    if state.pending_document:
        pending = state.pending_document
        summary = await summarize_document(pending)
        state.paid = False
        state.pending_document = None

        return {
            "type": "JOB_DONE",
            "data": {
                "message": "Payment confirmed and document summarized",
                "details": {
                    "summary": summary,
                    "original_length": len(pending),
                    "summary_length": len(summary),
                    "invoice_id": invoice_id,
                },
            },
        }

    return {
        "type": "PROGRESS",
        "data": {"message": "Payment confirmed. Send your summarize command."},
    }
