from __future__ import annotations

import hashlib
import hmac
import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Request

from app.core.config import settings
from app.services.invoice_service import InvoiceService

logger = logging.getLogger(__name__)
router = APIRouter()

_invoice_service = InvoiceService()


def _verify_circle_signature(body: bytes, signature: str | None) -> bool:
    """
    Circle signs every webhook with HMAC-SHA256 using the subscription secret.
    Header: X-Circle-Signature
    """
    if not signature:
        return False
    secret = settings.CIRCLE_WEBHOOK_SECRET
    if not secret:
        # Signature verification disabled when no secret is configured (dev mode)
        logger.warning("CIRCLE_WEBHOOK_SECRET not set — skipping signature verification")
        return True
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


@router.post("/webhooks/circle", include_in_schema=False)
async def handle_circle_webhook(request: Request) -> dict[str, bool]:
    """
    Receive Circle notifications.
    - transactions.inbound  → payment confirmation (escrow funded)
    - transactions.outbound → disbursement/refund state updates
    """
    body = await request.body()
    signature = request.headers.get("x-circle-signature")

    if not _verify_circle_signature(body, signature):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    data: dict[str, Any] = await request.json()
    notification_type: str = str(data.get("notificationType", ""))

    logger.debug("Circle webhook received: %s", notification_type)

    if notification_type == "transactions.inbound":
        await _invoice_service.handle_payment_webhook(data)

    elif notification_type == "webhooks.test":
        logger.info("Circle webhook test notification received")

    return {"received": True}
