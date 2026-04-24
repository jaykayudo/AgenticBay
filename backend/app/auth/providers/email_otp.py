from __future__ import annotations

import logging
from dataclasses import dataclass

from fastapi import BackgroundTasks
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.otp_store import OTPStore, generate_otp_code, normalize_email
from app.auth.rate_limiter import OTPSendRateLimiter
from app.auth.session_manager import IssuedTokenPair, SessionManager
from app.core.config import settings
from app.models.users import User, UserStatus

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class EmailMessage:
    to_email: str
    subject: str
    body: str


class EmailDelivery:
    async def send(self, message: EmailMessage) -> None:
        logger.info(
            "Sending OTP email to %s: %s\n%s",
            message.to_email,
            message.subject,
            message.body,
        )


class CircleWalletService:
    async def create_wallet_for_user(self, user_id: str, email: str) -> None:
        logger.info("Triggering Circle wallet creation for user %s (%s)", user_id, email)


@dataclass(slots=True)
class EmailOTPVerifyResult:
    tokens: IssuedTokenPair
    user: User
    is_new_user: bool


class EmailOTPProvider:
    def __init__(
        self,
        *,
        db: AsyncSession,
        otp_store: OTPStore,
        rate_limiter: OTPSendRateLimiter,
        email_delivery: EmailDelivery,
        circle_wallet_service: CircleWalletService,
    ):
        self.db = db
        self.otp_store = otp_store
        self.rate_limiter = rate_limiter
        self.email_delivery = email_delivery
        self.circle_wallet_service = circle_wallet_service

    async def send_otp(self, email: str) -> str:
        normalized_email = normalize_email(email)
        await self.rate_limiter.consume(normalized_email)
        code = generate_otp_code()
        await self.otp_store.store_code(normalized_email, code)
        await self.email_delivery.send(self._build_email_message(normalized_email, code))
        return normalized_email

    async def verify_otp(
        self,
        *,
        email: str,
        code: str,
        device_info: str | None,
        ip_address: str | None,
        background_tasks: BackgroundTasks,
    ) -> EmailOTPVerifyResult:
        normalized_email = normalize_email(email)
        await self.otp_store.verify_code(normalized_email, code)

        user = await self.db.scalar(select(User).where(User.email == normalized_email))
        is_new_user = user is None

        if user is None:
            user = User(
                email=normalized_email,
                display_name=None,
                role="BUYER",
                status=UserStatus.ACTIVE,
                email_verified=True,
            )
            self.db.add(user)
            await self.db.flush()
        else:
            user.email_verified = True

        tokens = await SessionManager(self.db).issue_tokens(
            user=user,
            device_info=device_info,
            ip_address=ip_address,
        )

        if is_new_user:
            background_tasks.add_task(
                self.circle_wallet_service.create_wallet_for_user,
                str(user.id),
                user.email,
            )

        return EmailOTPVerifyResult(tokens=tokens, user=user, is_new_user=is_new_user)

    @staticmethod
    def _build_email_message(email: str, code: str) -> EmailMessage:
        marketplace_name = settings.APP_NAME
        subject = f"Your sign-in code for {marketplace_name}"
        body = (
            f"Your {marketplace_name} sign-in code is: {code}\n\n"
            "This code expires in 10 minutes.\n\n"
            "If you did not request this code, you can safely ignore this email."
        )
        return EmailMessage(to_email=email, subject=subject, body=body)
