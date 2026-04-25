from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.auth.otp_store import OTPError, OTPStore
from app.auth.providers.email_otp import (
    CircleWalletService,
    EmailDelivery,
    EmailOTPProvider,
)
from app.auth.rate_limiter import OTPSendRateLimiter, OTPSendRateLimitError
from app.core.redis import get_redis
from app.schemas.auth import (
    AuthenticatedUserRead,
    RateLimitErrorResponse,
    SendOTPRequest,
    SendOTPResponse,
    VerifyOTPRequest,
    VerifyOTPResponse,
)

router = APIRouter(prefix="/auth/email", tags=["auth"])


def _request_metadata(request: Request) -> tuple[str | None, str | None]:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        ip_address = forwarded_for.split(",")[0].strip()
    elif request.client is not None:
        ip_address = request.client.host
    else:
        ip_address = None
    return request.headers.get("user-agent"), ip_address


def get_email_delivery() -> EmailDelivery:
    return EmailDelivery()


def get_circle_wallet_service() -> CircleWalletService:
    return CircleWalletService()


async def get_email_otp_provider(
    db: AsyncSession = Depends(get_session),
    email_delivery: EmailDelivery = Depends(get_email_delivery),
    circle_wallet_service: CircleWalletService = Depends(get_circle_wallet_service),
) -> EmailOTPProvider:
    redis = await get_redis()
    return EmailOTPProvider(
        db=db,
        otp_store=OTPStore(redis),
        rate_limiter=OTPSendRateLimiter(redis),
        email_delivery=email_delivery,
        circle_wallet_service=circle_wallet_service,
    )


@router.post(
    "/send-otp",
    response_model=SendOTPResponse,
    responses={429: {"model": RateLimitErrorResponse}},
)
async def send_otp(
    payload: SendOTPRequest,
    provider: EmailOTPProvider = Depends(get_email_otp_provider),
) -> SendOTPResponse | JSONResponse:
    try:
        normalized_email = await provider.send_otp(payload.email)
    except OTPSendRateLimitError as exc:
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "detail": "Too many OTP requests. Try again later.",
                "retry_after": exc.retry_after,
            },
            headers={"Retry-After": str(exc.retry_after)},
        )

    return SendOTPResponse(
        message="OTP sent to your email",
        expires_in_minutes=10,
        email=normalized_email,
    )


@router.post("/verify-otp", response_model=VerifyOTPResponse)
async def verify_otp(
    payload: VerifyOTPRequest,
    background_tasks: BackgroundTasks,
    request: Request,
    provider: EmailOTPProvider = Depends(get_email_otp_provider),
) -> VerifyOTPResponse:
    device_info, ip_address = _request_metadata(request)

    try:
        result = await provider.verify_otp(
            email=payload.email,
            code=payload.code,
            device_info=device_info,
            ip_address=ip_address,
            background_tasks=background_tasks,
        )
    except OTPError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    return VerifyOTPResponse(
        access_token=result.tokens.access_token,
        refresh_token=result.tokens.refresh_token,
        token_type="bearer",
        expires_in=result.tokens.expires_in,
        user=AuthenticatedUserRead(
            id=result.user.id,
            email=result.user.email,
            display_name=result.user.display_name,
            role=result.user.role,
            is_new_user=result.is_new_user,
        ),
    )
