from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.api.deps import get_session
from app.models.api_keys import ApiKey, ApiKeyEnvironment, ApiKeyPermission
from app.models.users import User
from app.services.api_key_service import (
    ALL_PERMISSIONS,
    MAX_ACTIVE_KEYS,
    ApiKeyLimitError,
    ApiKeyNotFoundError,
    ApiKeyService,
)

router = APIRouter(prefix="/keys", tags=["api-keys"])


class APIModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


class ApiKeyCreateRequest(APIModel):
    name: str = Field(min_length=1, max_length=100)
    environment: ApiKeyEnvironment
    permissions: list[ApiKeyPermission | str] = Field(default_factory=lambda: list(ALL_PERMISSIONS))
    expires_in_days: int | None = Field(default=None, ge=1, le=3650)

    @field_validator("permissions")
    @classmethod
    def normalize_permissions(cls, value: list[ApiKeyPermission | str]) -> list[str]:
        return [item.value if isinstance(item, ApiKeyPermission) else item for item in value]


class ApiKeyUpdateRequest(APIModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    permissions: list[ApiKeyPermission | str] | None = None

    @field_validator("permissions")
    @classmethod
    def normalize_permissions(cls, value: list[ApiKeyPermission | str] | None) -> list[str] | None:
        if value is None:
            return None
        return [item.value if isinstance(item, ApiKeyPermission) else item for item in value]


class ApiKeyRevokeRequest(APIModel):
    reason: str | None = Field(default=None, max_length=255)


class ApiKeyRead(APIModel):
    id: uuid.UUID
    name: str
    key_prefix: str
    environment: ApiKeyEnvironment
    permissions: list[Any]
    is_active: bool
    expires_at: datetime | None
    last_used_at: datetime | None
    usage_count: int
    revoked_at: datetime | None
    revoked_reason: str | None
    created_at: datetime
    updated_at: datetime


class ApiKeyCreatedResponse(ApiKeyRead):
    key: str
    warning: str = "Save this key securely. You will not see it again."


class ApiKeyUsageResponse(APIModel):
    key_id: str
    name: str
    usage_count: int
    last_used_at: str | None
    last_used_ip: str | None
    last_used_user_agent: str | None
    daily_usage: list[dict[str, Any]]
    recent_events: list[dict[str, Any]]


def _serialize_key(api_key: ApiKey) -> ApiKeyRead:
    return ApiKeyRead(
        id=api_key.id,
        name=api_key.name,
        key_prefix=api_key.key_prefix,
        environment=api_key.environment,
        permissions=api_key.permissions,
        is_active=api_key.is_active,
        expires_at=api_key.expires_at,
        last_used_at=api_key.last_used_at,
        usage_count=api_key.usage_count,
        revoked_at=api_key.revoked_at,
        revoked_reason=api_key.revoked_reason,
        created_at=api_key.created_at,
        updated_at=api_key.updated_at,
    )


def _client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",", 1)[0].strip()
    return request.client.host if request.client else None


def _map_service_error(exc: Exception) -> HTTPException:
    if isinstance(exc, ApiKeyNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(exc, ApiKeyLimitError):
        headers = {"Retry-After": str(exc.retry_after)} if exc.retry_after else None
        return HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(exc),
            headers=headers,
        )
    if isinstance(exc, ValueError):
        return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="API key operation failed.",
    )


@router.get("", response_model=list[ApiKeyRead])
async def list_api_keys(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> list[ApiKeyRead]:
    keys = await ApiKeyService(db).list_keys(current_user.id)
    return [_serialize_key(key) for key in keys]


@router.post("", response_model=ApiKeyCreatedResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    payload: ApiKeyCreateRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> ApiKeyCreatedResponse:
    try:
        created = await ApiKeyService(db).generate_key(
            user_id=current_user.id,
            name=payload.name,
            environment=payload.environment,
            permissions=[str(p) for p in payload.permissions],
            expires_in_days=payload.expires_in_days,
            ip=_client_ip(request),
            user_agent=request.headers.get("user-agent"),
        )
    except Exception as exc:
        raise _map_service_error(exc) from exc

    serialized = _serialize_key(created.api_key).model_dump()
    return ApiKeyCreatedResponse(**serialized, key=created.raw_key)


@router.get("/limits/current")
async def get_api_key_limits() -> dict[str, int]:
    return {"max_active_keys": MAX_ACTIVE_KEYS}


@router.get("/{key_id}", response_model=ApiKeyRead)
async def get_api_key(
    key_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> ApiKeyRead:
    try:
        key = await ApiKeyService(db).get_key(key_id, current_user.id)
        return _serialize_key(key)
    except Exception as exc:
        raise _map_service_error(exc) from exc


@router.patch("/{key_id}", response_model=ApiKeyRead)
async def update_api_key(
    key_id: uuid.UUID,
    payload: ApiKeyUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> ApiKeyRead:
    try:
        key = await ApiKeyService(db).update_key(
            key_id,
            current_user.id,
            name=payload.name,
            permissions=(
                [str(p) for p in payload.permissions] if payload.permissions is not None else None
            ),
        )
        return _serialize_key(key)
    except Exception as exc:
        raise _map_service_error(exc) from exc


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_api_key(
    key_id: uuid.UUID,
    request: Request,
    payload: ApiKeyRevokeRequest | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> Response:
    try:
        await ApiKeyService(db).revoke_key(
            key_id,
            current_user.id,
            reason=payload.reason if payload else None,
            ip=_client_ip(request),
            user_agent=request.headers.get("user-agent"),
        )
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except Exception as exc:
        raise _map_service_error(exc) from exc


@router.post("/{key_id}/rotate", response_model=ApiKeyCreatedResponse)
async def rotate_api_key(
    key_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> ApiKeyCreatedResponse:
    try:
        created = await ApiKeyService(db).rotate_key(
            key_id,
            current_user.id,
            ip=_client_ip(request),
            user_agent=request.headers.get("user-agent"),
        )
    except Exception as exc:
        raise _map_service_error(exc) from exc

    serialized = _serialize_key(created.api_key).model_dump()
    return ApiKeyCreatedResponse(**serialized, key=created.raw_key)


@router.get("/{key_id}/usage", response_model=ApiKeyUsageResponse)
async def get_api_key_usage(
    key_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> ApiKeyUsageResponse:
    try:
        usage = await ApiKeyService(db).get_usage(key_id, current_user.id)
        return ApiKeyUsageResponse(**usage)
    except Exception as exc:
        raise _map_service_error(exc) from exc
