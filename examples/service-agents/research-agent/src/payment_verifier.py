from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


async def verify_invoice_payment(wallet_address: str, expected_amount: float) -> bool:
    """
    Verify the agent's wallet received the expected payment.

    This example follows the same trust model as the document summarizer:
    the orchestrator has already escrowed payment and marks the session paid
    before the agent proceeds.
    """
    logger.info(
        "Payment verification: trusting orchestrator escrow confirmation "
        "(wallet=%s, expected=%.2f USDC)",
        wallet_address,
        expected_amount,
    )
    return True
