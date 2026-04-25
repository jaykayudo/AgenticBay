from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.services.wallet_service import CircleWebhookSignatureError, WalletService

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/circle", include_in_schema=False)
async def handle_circle_webhook(
    request: Request,
    db: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    body = await request.body()
    service = WalletService(db)
    try:
        service.verify_circle_signature(body, request.headers.get("x-circle-signature"))
        payload: dict[str, Any] = await request.json()
        tx = await service.handle_circle_webhook(payload)
    except CircleWebhookSignatureError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    return {"received": True, "transactionId": str(tx.id) if tx else None}
