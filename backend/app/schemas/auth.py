from __future__ import annotations

from datetime import datetime
from typing import Literal
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
    display_name: str | None
    role: str
    status: str
    email_verified: bool
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


class OAuthAuthorizationURLResponse(APIModel):
    auth_url: str


class SendOTPRequest(APIModel):
    email: str


class SendOTPResponse(APIModel):
    message: str
    expires_in_minutes: int
    email: str


class VerifyOTPRequest(APIModel):
    email: str
    code: str


class AuthenticatedUserRead(APIModel):
    id: UUID
    email: str
    display_name: str | None
    role: str
    is_new_user: bool


class VerifyOTPResponse(APIModel):
    access_token: str
    refresh_token: str
    token_type: Literal["bearer"]
    expires_in: int
    user: AuthenticatedUserRead


class RateLimitErrorResponse(APIModel):
    detail: str
    retry_after: int
