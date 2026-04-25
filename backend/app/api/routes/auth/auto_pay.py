from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.api.deps import get_session
from app.models.users import User

router = APIRouter(prefix="/auth", tags=["auth"])


class AutoPaySettingsRequest(BaseModel):
    auto_pay_enabled: bool
    auto_pay_max_per_job: float = Field(ge=0, default=10.0)
    auto_pay_max_per_day: float = Field(ge=0, default=50.0)


class AutoPaySettingsResponse(BaseModel):
    auto_pay_enabled: bool
    auto_pay_max_per_job: float | None
    auto_pay_max_per_day: float | None


@router.patch("/auto-pay", response_model=AutoPaySettingsResponse)
async def update_auto_pay(
    body: AutoPaySettingsRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> AutoPaySettingsResponse:
    """Update auto-pay settings for the marketplace user agent."""
    current_user.auto_pay_enabled = body.auto_pay_enabled
    current_user.auto_pay_max_per_job = Decimal(str(body.auto_pay_max_per_job))
    current_user.auto_pay_max_per_day = Decimal(str(body.auto_pay_max_per_day))
    await db.commit()

    return AutoPaySettingsResponse(
        auto_pay_enabled=current_user.auto_pay_enabled,
        auto_pay_max_per_job=float(current_user.auto_pay_max_per_job),
        auto_pay_max_per_day=float(current_user.auto_pay_max_per_day),
    )


@router.get("/auto-pay", response_model=AutoPaySettingsResponse)
async def get_auto_pay(
    current_user: User = Depends(get_current_user),
) -> AutoPaySettingsResponse:
    """Retrieve current auto-pay settings."""
    return AutoPaySettingsResponse(
        auto_pay_enabled=current_user.auto_pay_enabled,
        auto_pay_max_per_job=(
            float(current_user.auto_pay_max_per_job)
            if current_user.auto_pay_max_per_job is not None
            else None
        ),
        auto_pay_max_per_day=(
            float(current_user.auto_pay_max_per_day)
            if current_user.auto_pay_max_per_day is not None
            else None
        ),
    )
