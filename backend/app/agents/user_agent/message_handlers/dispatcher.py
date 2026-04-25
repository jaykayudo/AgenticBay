from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from app.agents.user_agent.message_handlers.close_appeal_handler import CloseAppealHandler
from app.agents.user_agent.message_handlers.connect_handler import ConnectHandler
from app.agents.user_agent.message_handlers.error_handler import ErrorHandler
from app.agents.user_agent.message_handlers.payment_handler import (
    PaymentConfirmedHandler,
    PaymentHandler,
)
from app.agents.user_agent.message_handlers.search_handler import SearchHandler
from app.agents.user_agent.message_handlers.service_handler import ServiceHandler

if TYPE_CHECKING:
    from app.agents.user_agent.agent import MarketplaceUserAgent

logger = logging.getLogger(__name__)

_HANDLER_MAP = {
    "SEARCH_AGENT": SearchHandler,
    "CONNECT": ConnectHandler,
    "SERVICE_AGENT": ServiceHandler,
    "PAYMENT": PaymentHandler,
    "PAYMENT_SUCCESSFUL": PaymentConfirmedHandler,
    "CLOSE_APPEAL": CloseAppealHandler,
    "ERROR": ErrorHandler,
}


class OrchestratorMessageDispatcher:
    def __init__(self, agent: MarketplaceUserAgent) -> None:
        self.agent = agent

    async def dispatch(self, message: dict[str, Any]) -> None:
        msg_type: str = message.get("type", "")
        handler_cls = _HANDLER_MAP.get(msg_type)

        if handler_cls is None:
            logger.warning(
                "[%s] No handler for orchestrator message type: %s", self.agent.session_id, msg_type
            )
            return

        handler = handler_cls(self.agent)
        await handler.handle(message)
