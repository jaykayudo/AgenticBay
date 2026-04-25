from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.agents.user_agent.agent import MarketplaceUserAgent


class PaymentHandler:
    def __init__(self, agent: MarketplaceUserAgent) -> None:
        self.agent = agent

    async def handle(self, message: dict[str, Any]) -> None:
        data = message.get("data", {})
        amount: float = data.get("amount", 0)
        description: str = data.get("description", "")
        payment_info: dict[str, Any] = data.get("payment_info", {})
        invoice_id: str = payment_info.get("invoice_id", "")
        escrow_wallet: str = payment_info.get("invoice_wallet", "")

        # Fetch the user's auto-pay settings for context
        auto_pay = await self.agent._get_auto_pay_settings()

        if auto_pay.auto_pay_enabled and amount <= auto_pay.auto_pay_max_per_job:
            auto_pay_context = (
                f"The user has auto_pay enabled with a per-job limit of "
                f"{auto_pay.auto_pay_max_per_job} USDC. "
                f"The requested amount ({amount} USDC) is within the limit. "
                "You may send PAYMENT_SUCCESSFUL directly without asking the user."
            )
        else:
            auto_pay_context = (
                "The user does not have auto_pay enabled or the amount exceeds their limit. "
                "You MUST use request_payment_confirmation to get explicit user approval."
            )

        context = (
            f"The orchestrator has requested payment:\n"
            f"  Amount: {amount} USDC\n"
            f"  Description: {description}\n"
            f"  Invoice ID: {invoice_id}\n"
            f"  Escrow wallet: {escrow_wallet}\n\n"
            f"{auto_pay_context}\n\n"
            "After payment is confirmed, send PAYMENT_SUCCESSFUL with the invoice_id."
        )

        await self.agent.memory.add_system_context(context)
        await self.agent.run_llm_turn()


class PaymentConfirmedHandler:
    def __init__(self, agent: MarketplaceUserAgent) -> None:
        self.agent = agent

    async def handle(self, message: dict[str, Any]) -> None:
        invoice_id: str = message.get("data", {}).get("invoice_id", "")
        context = (
            f"Payment confirmed by the orchestrator (invoice_id={invoice_id}). "
            "The service agent has been notified and will now process the request. "
            "Inform the user and await the result."
        )
        await self.agent.memory.add_system_context(context)
        await self.agent.run_llm_turn()
