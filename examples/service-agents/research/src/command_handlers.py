from __future__ import annotations

import logging
from typing import Any

from .config import settings
from .payment_verifier import verify_invoice_payment
from .researcher import ResearchError, run_research, validate_research_request
from .session_manager import SessionManager

logger = logging.getLogger(__name__)

RESEARCH_PRICE = "1.0"


async def handle_command(
    session_id: str,
    command: str,
    arguments: dict[str, Any],
    session_manager: SessionManager,
) -> dict[str, Any] | None:
    """Main command router."""
    handlers = {
        "research_topic": _handle_research_topic,
        "payment_confirmed": _handle_payment_confirmed,
    }

    handler = handlers.get(command)
    if handler is None:
        return {"type": "ERROR", "data": {"message": f"Unknown command: {command}"}}

    return await handler(session_id, arguments, session_manager)


async def _handle_research_topic(
    session_id: str,
    arguments: dict[str, Any],
    session_manager: SessionManager,
) -> dict[str, Any]:
    request_or_error = _build_research_request(arguments)
    if "error" in request_or_error:
        return {"type": "ERROR", "data": {"message": request_or_error["error"]}}

    state = session_manager.get(session_id)
    if state is None:
        return {"type": "ERROR", "data": {"message": "Session not found"}}

    if not state.paid:
        state.pending_research = request_or_error
        return {
            "type": "PAYMENT",
            "data": {
                "amount": RESEARCH_PRICE,
                "address": settings.AGENT_WALLET_ADDRESS,
                "description": "Payment for AI research report (1.0 USDC)",
            },
        }

    result = await _execute_research(request_or_error)
    if "error" in result:
        return {"type": "ERROR", "data": {"message": result["error"]}}

    state.paid = False
    state.pending_research = None

    return {
        "type": "JOB_DONE",
        "data": {
            "message": "Research report completed successfully",
            "details": result,
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
        expected_amount=float(RESEARCH_PRICE),
    )
    if not verified:
        return {"type": "ERROR", "data": {"message": "Payment verification failed"}}

    session_manager.mark_paid(session_id, invoice_id)

    if state.pending_research:
        pending = state.pending_research
        result = await _execute_research(pending)
        if "error" in result:
            return {"type": "ERROR", "data": {"message": result["error"]}}

        result["invoice_id"] = invoice_id
        state.paid = False
        state.pending_research = None

        return {
            "type": "JOB_DONE",
            "data": {
                "message": "Payment confirmed and research report completed",
                "details": result,
            },
        }

    return {
        "type": "PROGRESS",
        "data": {"message": "Payment confirmed. Send your research_topic command."},
    }


def _build_research_request(arguments: dict[str, Any]) -> dict[str, Any]:
    topic = str(arguments.get("topic", "")).strip()
    sources = arguments.get("sources", [])
    depth = str(arguments.get("depth", "standard")).strip().lower()
    max_sources = arguments.get("max_sources", 5)

    if not isinstance(sources, list):
        return {"error": "sources must be a list of URLs"}

    try:
        max_sources = int(max_sources)
    except (TypeError, ValueError):
        return {"error": "max_sources must be a number"}

    try:
        return validate_research_request(topic, sources, depth, max_sources)
    except ResearchError as exc:
        return {"error": str(exc)}


async def _execute_research(request: dict[str, Any]) -> dict[str, Any]:
    try:
        return await run_research(**request)
    except ResearchError as exc:
        logger.info("Research request failed: %s", exc)
        return {"error": str(exc)}
