from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class APIModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


class RefreshTokenRequest(APIModel):
    refresh_token: str


class TokenResponse(APIModel):
    access_token: str
    refresh_token: str
    expires_in: int


class UserProfileRead(APIModel):
    id: UUID
    email: str
    role: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class AuthSessionRead(APIModel):
    id: UUID
    device_info: str | None
    ip_address: str | None
    created_at: datetime
    last_used_at: datetime
    is_current: bool


class AuthSessionListResponse(APIModel):
    sessions: list[AuthSessionRead]


class LogoutAllResponse(APIModel):
    revoked_sessions: int
