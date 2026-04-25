from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Response,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_access_token
from app.api.deps import get_session
from app.api.routes.admin import get_admin_user
from app.api.routes.agents import get_active_user
from app.auth.jwt import AccessTokenPayload
from app.models.notifications import Notification, NotificationType
from app.models.users import User
from app.services.notification_service import NotificationService, notification_manager

router = APIRouter(prefix="/notifications", tags=["notifications"])


class APIModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


class PaginationMeta(APIModel):
    total: int
    page: int
    page_size: int = Field(alias="pageSize")
    has_next: bool = Field(alias="hasNext")


class NotificationRead(APIModel):
    id: UUID
    notification_type: NotificationType = Field(alias="notificationType")
    title: str
    body: str
    data: dict[str, Any]
    is_read: bool = Field(alias="isRead")
    read_at: datetime | None = Field(alias="readAt")
    created_at: datetime = Field(alias="createdAt")


class NotificationListResponse(APIModel):
    items: list[NotificationRead]
    unread_count: int = Field(alias="unreadCount")
    meta: PaginationMeta


class SendNotificationRequest(APIModel):
    user_id: UUID = Field(alias="userId")
    notification_type: NotificationType = Field(alias="notificationType")
    title: str = Field(min_length=1)
    body: str = Field(min_length=1)
    data: dict[str, Any] = Field(default_factory=dict)


class ReadAllResponse(APIModel):
    updated: int


def serialize_notification(notification: Notification) -> NotificationRead:
    return NotificationRead(
        id=notification.id,
        notificationType=notification.notification_type,
        title=notification.title,
        body=notification.body,
        data=notification.data,
        isRead=notification.is_read,
        readAt=notification.read_at,
        createdAt=notification.created_at,
    )


@router.get("", response_model=NotificationListResponse)
async def list_notifications(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    unread_only: bool = Query(default=False, alias="unreadOnly"),
    current_user: User = Depends(get_active_user),
    db: AsyncSession = Depends(get_session),
) -> NotificationListResponse:
    result = await NotificationService(db).list_notifications(
        current_user, page=page, page_size=page_size, unread_only=unread_only
    )
    return NotificationListResponse(
        items=[serialize_notification(notification) for notification in result.notifications],
        unreadCount=result.unread_count,
        meta=PaginationMeta(
            total=result.meta.total,
            page=result.meta.page,
            pageSize=result.meta.page_size,
            hasNext=result.meta.has_next,
        ),
    )


@router.patch("/{notification_id}/read", response_model=NotificationRead)
async def mark_notification_read(
    notification_id: UUID,
    current_user: User = Depends(get_active_user),
    db: AsyncSession = Depends(get_session),
) -> NotificationRead:
    try:
        notification = await NotificationService(db).mark_read(current_user, notification_id)
        return serialize_notification(notification)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.patch("/read-all", response_model=ReadAllResponse)
async def mark_all_notifications_read(
    current_user: User = Depends(get_active_user),
    db: AsyncSession = Depends(get_session),
) -> ReadAllResponse:
    updated = await NotificationService(db).mark_all_read(current_user)
    return ReadAllResponse(updated=updated)


@router.delete("/{notification_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_notification(
    notification_id: UUID,
    current_user: User = Depends(get_active_user),
    db: AsyncSession = Depends(get_session),
) -> Response:
    try:
        await NotificationService(db).delete_notification(current_user, notification_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/send", response_model=NotificationRead)
async def send_internal_notification(
    payload: SendNotificationRequest,
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_session),
) -> NotificationRead:
    del admin
    notification = await NotificationService(db).create_notification(
        user_id=payload.user_id,
        notification_type=payload.notification_type,
        title=payload.title,
        body=payload.body,
        data=payload.data,
    )
    return serialize_notification(notification)


@router.websocket("/ws")
async def notifications_websocket(websocket: WebSocket) -> None:
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4001)
        return

    try:
        payload: AccessTokenPayload = await get_current_access_token(token)
        user_id = UUID(payload.sub)
    except Exception:
        await websocket.close(code=4001)
        return

    await notification_manager.connect(user_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        notification_manager.disconnect(user_id, websocket)
