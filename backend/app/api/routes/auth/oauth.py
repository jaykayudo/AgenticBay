from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.core.config import settings
from app.schemas.auth import OAuthAuthorizationURLResponse

router = APIRouter(prefix="/auth", tags=["auth"])


def _oauth_authorization_url_response(
    provider_label: str, auth_url: str | None
) -> OAuthAuthorizationURLResponse:
    if not auth_url:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"{provider_label} sign-in is not configured.",
        )

    return OAuthAuthorizationURLResponse(auth_url=auth_url)


@router.get("/google", response_model=OAuthAuthorizationURLResponse)
async def google_auth_url() -> OAuthAuthorizationURLResponse:
    return _oauth_authorization_url_response("Google", settings.GOOGLE_AUTH_URL)


@router.get("/facebook", response_model=OAuthAuthorizationURLResponse)
async def facebook_auth_url() -> OAuthAuthorizationURLResponse:
    return _oauth_authorization_url_response("Facebook", settings.FACEBOOK_AUTH_URL)
