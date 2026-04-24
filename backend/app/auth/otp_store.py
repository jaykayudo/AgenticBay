from __future__ import annotations

import hashlib
import json
import secrets
from typing import Any

from app.core.config import settings


class OTPError(Exception):
    """Base exception for email OTP validation failures."""


class OTPExpiredError(OTPError):
    """Raised when an OTP is missing or has expired."""


class OTPInvalidCodeError(OTPError):
    """Raised when an OTP does not match."""


class OTPTooManyAttemptsError(OTPError):
    """Raised when too many invalid attempts invalidate the OTP."""


def normalize_email(email: str) -> str:
    return email.strip().lower()


def generate_otp_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def _hash_otp(email: str, code: str) -> str:
    payload = f"{settings.SECRET_KEY}:otp:{email}:{code}"
    return hashlib.sha256(payload.encode()).hexdigest()


class OTPStore:
    def __init__(self, redis: Any):
        self.redis = redis

    @staticmethod
    def _key(email: str) -> str:
        return f"otp:{normalize_email(email)}"

    async def store_code(self, email: str, code: str) -> None:
        normalized_email = normalize_email(email)
        payload = {"code_hash": _hash_otp(normalized_email, code), "attempts": 0}
        await self.redis.set(
            self._key(normalized_email),
            json.dumps(payload),
            ex=settings.EMAIL_OTP_EXPIRE_SECONDS,
        )

    async def verify_code(self, email: str, code: str) -> None:
        normalized_email = normalize_email(email)
        key = self._key(normalized_email)
        raw_payload = await self.redis.get(key)
        if raw_payload is None:
            raise OTPExpiredError("OTP code has expired. Request a new code.")

        payload = json.loads(raw_payload)
        provided_hash = _hash_otp(normalized_email, code)
        expected_hash = str(payload["code_hash"])

        if secrets.compare_digest(provided_hash, expected_hash):
            await self.redis.delete(key)
            return

        attempts = int(payload.get("attempts", 0)) + 1
        if attempts >= settings.EMAIL_OTP_MAX_ATTEMPTS:
            await self.redis.delete(key)
            raise OTPTooManyAttemptsError("Too many invalid attempts. Request a new code.")

        ttl = await self.redis.ttl(key)
        payload["attempts"] = attempts
        await self.redis.set(
            key,
            json.dumps(payload),
            ex=ttl if ttl and ttl > 0 else settings.EMAIL_OTP_EXPIRE_SECONDS,
        )
        remaining_attempts = settings.EMAIL_OTP_MAX_ATTEMPTS - attempts
        raise OTPInvalidCodeError(f"Invalid OTP code. {remaining_attempts} attempts remaining.")

    async def delete_code(self, email: str) -> None:
        await self.redis.delete(self._key(email))

    async def code_exists(self, email: str) -> bool:
        return bool(await self.redis.exists(self._key(email)))

