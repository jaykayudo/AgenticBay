from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.auth.otp_store import normalize_email
from app.core.config import settings


class OTPSendRateLimitError(Exception):
    """Raised when an email exceeds the OTP send rate limit."""

    def __init__(self, retry_after: int):
        super().__init__("Too many OTP requests. Try again later.")
        self.retry_after = retry_after


@dataclass(slots=True)
class OTPSendRateLimitResult:
    count: int
    retry_after: int | None


class OTPSendRateLimiter:
    def __init__(self, redis: Any):
        self.redis = redis

    @staticmethod
    def _key(email: str) -> str:
        return f"otp_rate:{normalize_email(email)}"

    async def consume(self, email: str) -> OTPSendRateLimitResult:
        key = self._key(email)
        count = int(await self.redis.incr(key))
        ttl = int(await self.redis.ttl(key))
        if ttl <= 0:
            await self.redis.expire(key, settings.EMAIL_OTP_RATE_LIMIT_WINDOW_SECONDS)
            ttl = settings.EMAIL_OTP_RATE_LIMIT_WINDOW_SECONDS

        if count > settings.EMAIL_OTP_RATE_LIMIT_MAX_REQUESTS:
            raise OTPSendRateLimitError(retry_after=ttl)

        return OTPSendRateLimitResult(count=count, retry_after=None)

