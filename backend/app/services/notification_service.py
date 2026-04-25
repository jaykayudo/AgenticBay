from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from fastapi import WebSocket
from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notifications import Notification, NotificationType
from app.models.users import User

logger = logging.getLogger(__name__)

CRITICAL_NOTIFICATION_TYPES = {
    NotificationType.JOB_COMPLETED,
    NotificationType.PAYMENT_RECEIVED,
    NotificationType.INVOICE_PAID,
}


@dataclass(frozen=True)
class PaginationMeta:
    total: int
    page: int
    page_size: int
    has_next: bool


@dataclass(frozen=True)
class NotificationListResult:
    notifications: list[Notification]
    unread_count: int
    meta: PaginationMeta


class NotificationConnectionManager:
    def __init__(self) -> None:
        self._connections: dict[uuid.UUID, set[WebSocket]] = {}

    async def connect(self, user_id: uuid.UUID, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.setdefault(user_id, set()).add(websocket)

    def disconnect(self, user_id: uuid.UUID, websocket: WebSocket) -> None:
        sockets = self._connections.get(user_id)
        if sockets is None:
            return
        sockets.discard(websocket)
        if not sockets:
            self._connections.pop(user_id, None)

    async def push(self, user_id: uuid.UUID, payload: dict[str, Any]) -> None:
        sockets = list(self._connections.get(user_id, set()))
        for socket in sockets:
            try:
                await socket.send_json(payload)
            except Exception:
                self.disconnect(user_id, socket)


notification_manager = NotificationConnectionManager()


class NotificationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_notification(
        self,
        *,
        user_id: uuid.UUID,
        notification_type: NotificationType,
        title: str,
        body: str,
        data: dict[str, Any] | None = None,
        enqueue_email: bool = True,
    ) -> Notification:
        notification = Notification(
            user_id=user_id,
            notification_type=notification_type,
            title=title,
            body=body,
            data=data or {},
        )
        self.db.add(notification)
        await self.db.flush()
        await self.db.commit()
        await self.db.refresh(notification)

        await notification_manager.push(user_id, self.serialize(notification))
        if enqueue_email and notification_type in CRITICAL_NOTIFICATION_TYPES:
            asyncio.create_task(self.deliver_email(notification.id))
        return notification

    async def list_notifications(
        self, user: User, *, page: int = 1, page_size: int = 20, unread_only: bool = False
    ) -> NotificationListResult:
        page = max(1, page)
        page_size = min(max(1, page_size), 100)
        stmt = select(Notification).where(Notification.user_id == user.id)
        if unread_only:
            stmt = stmt.where(Notification.is_read.is_(False))

        total = await self._count(stmt)
        unread_count = await self.unread_count(user)
        result = await self.db.execute(
            stmt.order_by(Notification.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return NotificationListResult(
            notifications=list(result.scalars().all()),
            unread_count=unread_count,
            meta=PaginationMeta(
                total=total,
                page=page,
                page_size=page_size,
                has_next=page * page_size < total,
            ),
        )

    async def unread_count(self, user: User) -> int:
        total = await self.db.scalar(
            select(func.count())
            .select_from(Notification)
            .where(Notification.user_id == user.id, Notification.is_read.is_(False))
        )
        return int(total or 0)

    async def mark_read(self, user: User, notification_id: uuid.UUID) -> Notification:
        notification = await self.db.get(Notification, notification_id)
        if notification is None or notification.user_id != user.id:
            raise LookupError("Notification not found.")
        notification.is_read = True
        notification.read_at = datetime.now(UTC)
        await self.db.commit()
        await self.db.refresh(notification)
        return notification

    async def mark_all_read(self, user: User) -> int:
        result = await self.db.execute(
            select(Notification).where(
                Notification.user_id == user.id,
                Notification.is_read.is_(False),
            )
        )
        notifications = list(result.scalars().all())
        now = datetime.now(UTC)
        for notification in notifications:
            notification.is_read = True
            notification.read_at = now
        await self.db.commit()
        return len(notifications)

    async def delete_notification(self, user: User, notification_id: uuid.UUID) -> None:
        notification = await self.db.get(Notification, notification_id)
        if notification is None or notification.user_id != user.id:
            raise LookupError("Notification not found.")
        await self.db.delete(notification)
        await self.db.commit()

    async def deliver_email(self, notification_id: uuid.UUID) -> None:
        logger.info("Queued critical notification email for notification=%s", notification_id)

    async def _count(self, stmt: Select[tuple[Notification]]) -> int:
        subquery = stmt.with_only_columns(Notification.id).order_by(None).subquery()
        total = await self.db.scalar(select(func.count()).select_from(subquery))
        return int(total or 0)

    @staticmethod
    def serialize(notification: Notification) -> dict[str, Any]:
        return {
            "id": str(notification.id),
            "type": notification.notification_type.value,
            "title": notification.title,
            "body": notification.body,
            "data": notification.data,
            "isRead": notification.is_read,
            "readAt": notification.read_at.isoformat() if notification.read_at else None,
            "createdAt": notification.created_at.isoformat(),
        }
