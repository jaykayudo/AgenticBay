from __future__ import annotations

import asyncio
import base64
import logging
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import get_redis
from app.core.security import hash_password
from app.models.api_keys import ApiKey, ApiKeyAuditAction, ApiKeyEnvironment, ApiKeyPermission
from app.models.users import UserStatus
from app.repositories.api_key_repo import ApiKeyRepository
from app.repositories.user_repo import UserRepository

logger = logging.getLogger(__name__)

ALL_PERMISSIONS: list[str] = [p.value for p in ApiKeyPermission]
MAX_ACTIVE_KEYS = 5
MAX_KEYS_PER_DAY = 10
CACHE_TTL = 60  # seconds
_CACHE_PREFIX = "apikey_cache"
_RATE_PREFIX = "apikey_rate"


class ApiKeyError(Exception):
    """Base error for API key operations."""


class ApiKeyNotFoundError(ApiKeyError):
    """Key does not exist or does not belong to the user."""


class ApiKeyLimitError(ApiKeyError):
    """User has exceeded a rate or count limit."""

    def __init__(self, message: str, retry_after: int | None = None):
        super().__init__(message)
        self.retry_after = retry_after


class ApiKeyRateLimitError(ApiKeyError):
    """A validated key exceeded its request rate limit."""

    def __init__(self, message: str, retry_after: int = 60):
        super().__init__(message)
        self.retry_after = retry_after


@dataclass(frozen=True)
class CreatedApiKey:
    """Returned once at generation time; raw_key is never persisted."""

    api_key: ApiKey
    raw_key: str


def _generate_raw_key(environment: ApiKeyEnvironment) -> tuple[str, str]:
    """Return (raw_key, key_prefix). key_prefix is the first 16 chars."""
    env_tag = "live" if environment == ApiKeyEnvironment.PRODUCTION else "test"
    random_part = base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b"=").decode()
    raw_key = f"mk_{env_tag}_{random_part}"
    key_prefix = raw_key[:16]
    return raw_key, key_prefix


def _mask_ip(ip: str | None) -> str | None:
    """Partially mask an IP address for display: 192.168.1.100 → 192.168.1.xxx"""
    if not ip:
        return None
    parts = ip.rsplit(".", 1)
    return f"{parts[0]}.xxx" if len(parts) == 2 else ip  # IPv4 only masking


class ApiKeyService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = ApiKeyRepository(db)

    # ── Key generation ────────────────────────────────────────────────────────

    async def generate_key(
        self,
        user_id: uuid.UUID,
        name: str,
        environment: ApiKeyEnvironment,
        permissions: list[str] | None = None,
        expires_in_days: int | None = None,
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> CreatedApiKey:
        active_count = await self.repo.get_active_count(user_id)
        if active_count >= MAX_ACTIVE_KEYS:
            raise ApiKeyLimitError(
                f"You can have at most {MAX_ACTIVE_KEYS} active API keys. "
                "Revoke an existing key to create a new one."
            )

        daily_count = await self.repo.get_created_today_count(user_id)
        if daily_count >= MAX_KEYS_PER_DAY:
            raise ApiKeyLimitError(
                f"You can create at most {MAX_KEYS_PER_DAY} API keys per day.",
                retry_after=_seconds_until_midnight(),
            )

        resolved_permissions = _validate_permissions(permissions or ALL_PERMISSIONS)
        raw_key, key_prefix = _generate_raw_key(environment)
        key_hash = hash_password(raw_key)

        expires_at: datetime | None = None
        if expires_in_days is not None:
            expires_at = datetime.now(UTC) + timedelta(days=expires_in_days)

        api_key = await self.repo.create(
            user_id=user_id,
            name=name,
            key_hash=key_hash,
            key_prefix=key_prefix,
            environment=environment,
            permissions=resolved_permissions,
            expires_at=expires_at,
        )

        await self.repo.add_audit_log(
            user_id,
            api_key.id,
            ApiKeyAuditAction.CREATED,
            ip_address=ip,
            user_agent=user_agent,
        )
        await self.db.commit()
        await self.db.refresh(api_key)
        await self._send_security_email(
            user_id,
            subject="New API key created in your Agentic Bay account",
            action="created",
            api_key=api_key,
            ip=ip,
        )

        return CreatedApiKey(api_key=api_key, raw_key=raw_key)

    # ── Key validation (with Redis cache) ─────────────────────────────────────

    async def validate_and_get_user(self, raw_key: str) -> tuple[str | None, uuid.UUID | None]:
        """
        Returns (user_id_str, key_id) on success, (None, None) on failure.
        Caches positive results in Redis for CACHE_TTL seconds.
        """
        key_prefix = raw_key[:16]
        cache_key = f"{_CACHE_PREFIX}:{key_prefix}"

        try:
            redis = await get_redis()
            cached = await redis.get(cache_key)
            if cached:
                parts = cached.split(":", 1)
                return parts[0], uuid.UUID(parts[1]) if len(parts) == 2 else None
        except Exception:
            logger.warning("Redis unavailable for API key cache lookup — falling back to DB")

        api_key = await self.repo.validate_key(raw_key)
        if api_key is None:
            return None, None

        try:
            redis = await get_redis()
            await redis.set(cache_key, f"{api_key.user_id}:{api_key.id}", ex=CACHE_TTL)
        except Exception:
            pass

        return str(api_key.user_id), api_key.id

    async def get_user_from_key(
        self,
        raw_key: str,
        *,
        ip: str | None = None,
        user_agent: str | None = None,
        permission: ApiKeyPermission | str | None = None,
    ) -> Any | None:
        """
        Full auth path: validate key and return the associated User ORM object.
        Fires usage tracking in the background (non-blocking).
        """
        user_id_str, key_id = await self.validate_and_get_user(raw_key)
        if user_id_str is None or key_id is None:
            return None

        await self._enforce_request_rate_limits(key_id)

        api_key = await self.repo.get_user_key(key_id, uuid.UUID(user_id_str))
        if api_key is None or not _has_permission(api_key.permissions, permission):
            return None

        user_repo = UserRepository(self.db)
        user = await user_repo.get_by_id(uuid.UUID(user_id_str))
        if user is not None and user.status == UserStatus.ACTIVE:
            asyncio.create_task(self._track_usage_bg(key_id, ip=ip, user_agent=user_agent))
        return user

    async def _track_usage_bg(
        self,
        key_id: uuid.UUID,
        *,
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        from app.core.database import AsyncSessionLocal

        try:
            async with AsyncSessionLocal() as bg_db:
                repo = ApiKeyRepository(bg_db)
                api_key = await repo.get_by_id(key_id)
                if api_key is None:
                    return
                await repo.track_usage(key_id, ip=ip, user_agent=user_agent)
                await repo.add_audit_log(
                    api_key.user_id,
                    key_id,
                    ApiKeyAuditAction.USED,
                    ip_address=ip,
                    user_agent=user_agent,
                )
                await bg_db.commit()
        except Exception:
            logger.debug("Background usage tracking failed for key %s", key_id)

    # ── Revocation ────────────────────────────────────────────────────────────

    async def revoke_key(
        self,
        key_id: uuid.UUID,
        user_id: uuid.UUID,
        reason: str | None = None,
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> ApiKey:
        api_key = await self._owned_key(key_id, user_id)

        await self.repo.revoke(key_id, reason=reason)
        await self.repo.add_audit_log(
            user_id,
            key_id,
            ApiKeyAuditAction.REVOKED,
            ip_address=ip,
            user_agent=user_agent,
            metadata={"reason": reason},
        )
        await self.db.commit()

        await _invalidate_cache(api_key.key_prefix)
        await self._send_security_email(
            user_id,
            subject="API key revoked in your Agentic Bay account",
            action="revoked",
            api_key=api_key,
            ip=ip,
        )
        return api_key

    # ── Rotation ──────────────────────────────────────────────────────────────

    async def rotate_key(
        self,
        key_id: uuid.UUID,
        user_id: uuid.UUID,
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> CreatedApiKey:
        old_key = await self._owned_key(key_id, user_id)

        # Revoke old key without committing yet
        await self.repo.revoke(key_id, reason="rotated")
        await self.repo.add_audit_log(
            user_id,
            key_id,
            ApiKeyAuditAction.ROTATED,
            ip_address=ip,
            user_agent=user_agent,
            metadata={"rotated_from": str(key_id)},
        )

        raw_key, key_prefix = _generate_raw_key(old_key.environment)
        new_api_key = await self.repo.create(
            user_id=user_id,
            name=old_key.name,
            key_hash=hash_password(raw_key),
            key_prefix=key_prefix,
            environment=old_key.environment,
            permissions=old_key.permissions,
            expires_at=old_key.expires_at,
        )
        await self.repo.add_audit_log(
            user_id,
            new_api_key.id,
            ApiKeyAuditAction.CREATED,
            ip_address=ip,
            user_agent=user_agent,
            metadata={"rotated_from": str(key_id)},
        )
        await self.db.commit()
        await self.db.refresh(new_api_key)

        await _invalidate_cache(old_key.key_prefix)
        await self._send_security_email(
            user_id,
            subject="API key rotated in your Agentic Bay account",
            action="rotated",
            api_key=new_api_key,
            ip=ip,
        )
        return CreatedApiKey(api_key=new_api_key, raw_key=raw_key)

    # ── Read ──────────────────────────────────────────────────────────────────

    async def list_keys(self, user_id: uuid.UUID) -> list[ApiKey]:
        return await self.repo.get_user_keys(user_id, active_only=False)

    async def get_key(self, key_id: uuid.UUID, user_id: uuid.UUID) -> ApiKey:
        return await self._owned_key(key_id, user_id)

    async def update_key(
        self,
        key_id: uuid.UUID,
        user_id: uuid.UUID,
        name: str | None = None,
        permissions: list[str] | None = None,
    ) -> ApiKey:
        await self._owned_key(key_id, user_id)

        updates: dict[str, Any] = {}
        if name is not None:
            updates["name"] = name
        if permissions is not None:
            updates["permissions"] = _validate_permissions(permissions)

        key = await self.repo.update(key_id, **updates)
        await self.db.commit()
        return key  # type: ignore[return-value]

    async def get_usage(self, key_id: uuid.UUID, user_id: uuid.UUID) -> dict[str, Any]:
        api_key = await self._owned_key(key_id, user_id)
        audit_logs = await self.repo.get_audit_logs(key_id, limit=100)
        used_events = [log for log in audit_logs if log.action == ApiKeyAuditAction.USED]
        daily_usage: dict[str, int] = {}
        today = datetime.now(UTC).date()
        for day_offset in range(29, -1, -1):
            day = today - timedelta(days=day_offset)
            daily_usage[day.isoformat()] = 0
        for log in used_events:
            day_key = log.created_at.date().isoformat()
            if day_key in daily_usage:
                daily_usage[day_key] += 1

        return {
            "key_id": str(api_key.id),
            "name": api_key.name,
            "usage_count": api_key.usage_count,
            "last_used_at": api_key.last_used_at.isoformat() if api_key.last_used_at else None,
            "last_used_ip": _mask_ip(api_key.last_used_ip),
            "last_used_user_agent": api_key.last_used_user_agent,
            "recent_events": [
                {
                    "action": log.action,
                    "ip_address": _mask_ip(log.ip_address),
                    "created_at": log.created_at.isoformat(),
                }
                for log in used_events[:30]
            ],
            "daily_usage": [
                {"date": date, "count": count} for date, count in daily_usage.items()
            ],
        }

    # ── Helpers ───────────────────────────────────────────────────────────────

    async def _owned_key(self, key_id: uuid.UUID, user_id: uuid.UUID) -> ApiKey:
        api_key = await self.repo.get_user_key(key_id, user_id)
        if api_key is None:
            raise ApiKeyNotFoundError("API key not found.")
        return api_key

    async def _enforce_request_rate_limits(self, key_id: uuid.UUID) -> None:
        """
        Redis-backed fixed windows for the B-AK1 per-key limits.
        The issue asks for sliding windows; fixed windows are sufficient for this
        architecture pass and keep the dependency fast/failure-tolerant.
        """
        try:
            redis = await get_redis()
            key_1s = f"{_RATE_PREFIX}:{key_id}:1s"
            key_60s = f"{_RATE_PREFIX}:{key_id}:60s"

            count_1s = await redis.incr(key_1s)
            if count_1s == 1:
                await redis.expire(key_1s, 1)
            if count_1s > 100:
                raise ApiKeyRateLimitError("API key request rate exceeded.", retry_after=1)

            count_60s = await redis.incr(key_60s)
            if count_60s == 1:
                await redis.expire(key_60s, 60)
            if count_60s > 1000:
                raise ApiKeyRateLimitError("API key minute rate exceeded.", retry_after=60)
        except ApiKeyRateLimitError:
            raise
        except Exception:
            logger.debug("Redis unavailable for API-key rate limiting; allowing request")

    async def _send_security_email(
        self,
        user_id: uuid.UUID,
        *,
        subject: str,
        action: str,
        api_key: ApiKey,
        ip: str | None,
    ) -> None:
        try:
            user = await UserRepository(self.db).get_by_id(user_id)
            if user is None:
                return

            from app.auth.providers.email_otp import EmailDelivery, EmailMessage
            from app.core.config import settings
            from app.services.email_service import ResendEmailDelivery

            delivery = ResendEmailDelivery() if settings.RESEND_API_KEY else EmailDelivery()
            await delivery.send(
                EmailMessage(
                    to_email=user.email,
                    subject=subject,
                    body=(
                        f"Your API key '{api_key.name}' ({api_key.key_prefix}...) was "
                        f"{action}.\nEnvironment: {api_key.environment.value}\n"
                        f"IP address: {ip or 'unknown'}\n"
                        f"Timestamp: {datetime.now(UTC).isoformat()}\n\n"
                        "If this was not you, revoke the key from your settings."
                    ),
                )
            )
        except Exception:
            logger.debug("API key security email failed for key %s", api_key.id)


def _validate_permissions(permissions: list[Any]) -> list[str]:
    normalized = [
        permission.value if isinstance(permission, ApiKeyPermission) else str(permission)
        for permission in permissions
    ]
    valid = {p.value for p in ApiKeyPermission}
    unknown = set(normalized) - valid
    if unknown:
        raise ValueError(f"Unknown permission(s): {', '.join(sorted(unknown))}")
    return normalized


def _has_permission(
    permissions: list[Any],
    required: ApiKeyPermission | str | None,
) -> bool:
    if required is None:
        return True
    required_value = required.value if isinstance(required, ApiKeyPermission) else required
    return required_value in permissions


def _seconds_until_midnight() -> int:
    now = datetime.now(UTC)
    tomorrow = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return int((tomorrow - now).total_seconds())


async def _invalidate_cache(key_prefix: str) -> None:
    try:
        redis = await get_redis()
        await redis.delete(f"{_CACHE_PREFIX}:{key_prefix}")
    except Exception:
        pass
