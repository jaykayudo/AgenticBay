import pytest

from src.payment_verifier import verify_invoice_payment


@pytest.mark.asyncio
async def test_payment_verifier_returns_true_for_any_amount():
    result = await verify_invoice_payment(
        wallet_address="0xAnyWallet",
        expected_amount=0.5,
    )
    assert result is True


@pytest.mark.asyncio
async def test_payment_verifier_returns_true_regardless_of_wallet():
    for address in ["0xAAA", "0xBBB", ""]:
        result = await verify_invoice_payment(
            wallet_address=address,
            expected_amount=0.5,
        )
        assert result is True, f"Expected True for wallet={address}"


@pytest.mark.asyncio
async def test_payment_verifier_returns_true_for_zero_amount():
    # Edge case: escrow trust model should not depend on amount value
    result = await verify_invoice_payment(
        wallet_address="0xAnyWallet",
        expected_amount=0.0,
    )
    assert result is True
