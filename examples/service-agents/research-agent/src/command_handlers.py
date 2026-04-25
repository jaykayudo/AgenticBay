from __future__ import annotations

import json
import logging
from typing import Any

from .config import settings
from .models import ResearchArguments
from .payment_verifier import verify_invoice_payment
from .researcher import research_topic
from .session_manager import SessionManager

logger = logging.getLogger(__name__)

RESEARCH_PRICE = "0.01"
MAX_CONTEXT_LENGTH = 60_000


async def handle_command(
    session_id: str,
    command: str,
    arguments: dict[str, Any],
    session_manager: SessionManager,
) -> dict[str, Any] | None:
    handlers = {
        "research": _handle_research,
        "payment_confirmed": _handle_payment_confirmed,
    }

    handler = handlers.get(command)
    if handler is None:
        return {"type": "ERROR", "data": {"message": f"Unknown command: {command}"}}

    return await handler(session_id, arguments, session_manager)


async def _handle_research(
    session_id: str,
    arguments: dict[str, Any],
    session_manager: SessionManager,
) -> dict[str, Any]:
    topic = str(arguments.get("topic", "")).strip()
    context = str(arguments.get("context", "")).strip()
    focus_areas = arguments.get("focus_areas") or []
    constraints = arguments.get("constraints") or []

    if not topic:
        return {"type": "ERROR", "data": {"message": "Topic cannot be empty"}}

    if len(context) > MAX_CONTEXT_LENGTH:
        return {
            "type": "ERROR",
            "data": {"message": f"Context exceeds maximum length of {MAX_CONTEXT_LENGTH} characters"},
        }

    state = session_manager.get(session_id)
    if state is None:
        return {"type": "ERROR", "data": {"message": "Session not found"}}

    if not state.paid:
        state.pending_topic = topic
        state.pending_context = context or None
        state.pending_focus_areas = [str(item) for item in focus_areas]
        state.pending_constraints = [str(item) for item in constraints]
        return {
            "type": "PAYMENT",
            "data": {
                "amount": RESEARCH_PRICE,
                "address": settings.AGENT_WALLET_ADDRESS,
                "description": "Payment for research brief (0.01 USDC)",
            },
        }

    brief = await research_topic(
        ResearchArguments(
            topic=topic,
            context=context or None,
            focus_areas=[str(item) for item in focus_areas] or None,
            constraints=[str(item) for item in constraints] or None,
        )
    )
    state.paid = False
    state.pending_topic = None
    state.pending_context = None
    state.pending_focus_areas = []
    state.pending_constraints = []

    return {
        "type": "JOB_DONE",
        "data": {
            "message": "Research completed successfully",
            "details": json.loads(brief.model_dump_json()),
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

    session_manager.mark_paid(session_id, str(invoice_id))

    if state.pending_topic:
        brief = await research_topic(
            ResearchArguments(
                topic=state.pending_topic,
                context=state.pending_context,
                focus_areas=state.pending_focus_areas or None,
                constraints=state.pending_constraints or None,
            )
        )
        state.paid = False
        state.pending_topic = None
        state.pending_context = None
        state.pending_focus_areas = []
        state.pending_constraints = []

        return {
            "type": "JOB_DONE",
            "data": {
                "message": "Payment confirmed and research completed",
                "details": json.loads(brief.model_dump_json()),
            },
        }

    return {
        "type": "PROGRESS",
        "data": {"message": "Payment confirmed. Send your research command."},
    }
