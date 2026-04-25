from __future__ import annotations

import logging
from typing import Any

from .config import settings
from .payment_verifier import verify_invoice_payment
from .scraper import (
    MAX_TEXT_CHARS,
    ScraperError,
    extract_structured_data,
    scrape_url,
    validate_url,
)
from .session_manager import SessionManager

logger = logging.getLogger(__name__)

SCRAPE_PRICE = "0.2"


async def handle_command(
    session_id: str,
    command: str,
    arguments: dict[str, Any],
    session_manager: SessionManager,
) -> dict[str, Any] | None:
    """Main command router."""
    handlers = {
        "scrape_url": _handle_scrape_url,
        "extract_structured_data": _handle_extract_structured_data,
        "payment_confirmed": _handle_payment_confirmed,
    }

    handler = handlers.get(command)
    if handler is None:
        return {"type": "ERROR", "data": {"message": f"Unknown command: {command}"}}

    return await handler(session_id, arguments, session_manager)


async def _handle_scrape_url(
    session_id: str,
    arguments: dict[str, Any],
    session_manager: SessionManager,
) -> dict[str, Any]:
    request_or_error = _build_scrape_request(arguments)
    if "error" in request_or_error:
        return {"type": "ERROR", "data": {"message": request_or_error["error"]}}
    request_or_error["operation"] = "scrape_url"

    state = session_manager.get(session_id)
    if state is None:
        return {"type": "ERROR", "data": {"message": "Session not found"}}

    if not state.paid:
        state.pending_scrape = request_or_error
        return {
            "type": "PAYMENT",
            "data": {
                "amount": SCRAPE_PRICE,
                "address": settings.AGENT_WALLET_ADDRESS,
                "description": "Payment for web page scraping (0.2 USDC)",
            },
        }

    result = await _execute_request(request_or_error)
    if "error" in result:
        return {"type": "ERROR", "data": {"message": result["error"]}}

    state.paid = False
    state.pending_scrape = None

    return {
        "type": "JOB_DONE",
        "data": {
            "message": "URL scraped successfully",
            "details": result,
        },
    }


async def _handle_extract_structured_data(
    session_id: str,
    arguments: dict[str, Any],
    session_manager: SessionManager,
) -> dict[str, Any]:
    request_or_error = _build_structured_data_request(arguments)
    if "error" in request_or_error:
        return {"type": "ERROR", "data": {"message": request_or_error["error"]}}
    request_or_error["operation"] = "extract_structured_data"

    state = session_manager.get(session_id)
    if state is None:
        return {"type": "ERROR", "data": {"message": "Session not found"}}

    if not state.paid:
        state.pending_scrape = request_or_error
        return {
            "type": "PAYMENT",
            "data": {
                "amount": SCRAPE_PRICE,
                "address": settings.AGENT_WALLET_ADDRESS,
                "description": "Payment for structured web data extraction (0.2 USDC)",
            },
        }

    result = await _execute_request(request_or_error)
    if "error" in result:
        return {"type": "ERROR", "data": {"message": result["error"]}}

    state.paid = False
    state.pending_scrape = None

    return {
        "type": "JOB_DONE",
        "data": {
            "message": "Structured data extracted successfully",
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
        expected_amount=float(SCRAPE_PRICE),
    )
    if not verified:
        return {"type": "ERROR", "data": {"message": "Payment verification failed"}}

    session_manager.mark_paid(session_id, invoice_id)

    if state.pending_scrape:
        pending = state.pending_scrape
        result = await _execute_request(pending)
        if "error" in result:
            return {"type": "ERROR", "data": {"message": result["error"]}}

        result["invoice_id"] = invoice_id
        state.paid = False
        state.pending_scrape = None

        return {
            "type": "JOB_DONE",
            "data": {
                "message": "Payment confirmed and request completed",
                "details": result,
            },
        }

    return {
        "type": "PROGRESS",
        "data": {
            "message": (
                "Payment confirmed. Send your scrape_url or "
                "extract_structured_data command."
            )
        },
    }


def _build_scrape_request(arguments: dict[str, Any]) -> dict[str, Any]:
    url = str(arguments.get("url", "")).strip()
    include_links = bool(arguments.get("include_links", False))
    max_chars = arguments.get("max_chars")

    if not url:
        return {"error": "URL cannot be empty"}

    try:
        url = validate_url(url)
    except ScraperError as exc:
        return {"error": str(exc)}

    if max_chars is not None:
        try:
            max_chars = int(max_chars)
        except (TypeError, ValueError):
            return {"error": "max_chars must be a number"}

        if max_chars < 1 or max_chars > MAX_TEXT_CHARS:
            return {"error": f"max_chars must be between 1 and {MAX_TEXT_CHARS}"}

    return {
        "url": url,
        "include_links": include_links,
        "max_chars": max_chars,
    }


def _build_structured_data_request(arguments: dict[str, Any]) -> dict[str, Any]:
    url = str(arguments.get("url", "")).strip()

    if not url:
        return {"error": "URL cannot be empty"}

    try:
        url = validate_url(url)
    except ScraperError as exc:
        return {"error": str(exc)}

    return {
        "url": url,
        "include_links": bool(arguments.get("include_links", True)),
        "include_tables": bool(arguments.get("include_tables", True)),
        "include_json_ld": bool(arguments.get("include_json_ld", True)),
    }


async def _execute_request(request: dict[str, Any]) -> dict[str, Any]:
    operation = request.get("operation", "scrape_url")
    kwargs = {key: value for key, value in request.items() if key != "operation"}

    try:
        if operation == "extract_structured_data":
            return await extract_structured_data(**kwargs)

        return await scrape_url(**kwargs)
    except ScraperError as exc:
        logger.info("Web scraper request failed: %s", exc)
        return {"error": str(exc)}
