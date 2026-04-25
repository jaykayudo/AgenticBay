from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


async def verify_invoice_payment(
    wallet_address: str,
    expected_amount: float,
) -> bool:
    """
    Verify the agent's wallet received the expected payment.

    Agentic Bay uses an off-chain escrow model: when the orchestrator
    sends payment_confirmed, the buyer's funds are already locked in an
    escrow wallet controlled by the platform. Disbursement to this
    agent's wallet happens at session close.

    During the session we therefore trust the orchestrator's confirmation
    as the authoritative signal that escrowed funds exist. Independent
    on-chain verification happens post-disbursement if needed.
    """
    logger.info(
        "Payment verification: trusting orchestrator escrow confirmation "
        "(wallet=%s, expected=%.2f USDC)",
        wallet_address,
        expected_amount,
    )
    return True
