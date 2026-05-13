from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any

_EXPLORER_URLS: dict[str, str] = {
    "ARC-TESTNET": "https://explorer.arcana.network/tx/",
    "ETH-SEPOLIA": "https://sepolia.etherscan.io/tx/",
    "ETH": "https://etherscan.io/tx/",
    "ARB": "https://arbiscan.io/tx/",
    "MATIC-AMOY": "https://amoy.polygonscan.com/tx/",
    "MATIC": "https://polygonscan.com/tx/",
}


@dataclass
class WalletInfo:
    wallet_id: str
    address: str
    blockchain: str
    state: str = "LIVE"


@dataclass
class TransferResult:
    """Result of a payment transfer operation."""

    transfer_id: str
    state: str  # "PENDING" | "COMPLETE" | "FAILED" | "CANCELLED"
    tx_hash: str | None = None


@dataclass
class TransactionInfo:
    """Details of a single wallet transaction (inbound or outbound)."""

    transaction_id: str
    direction: str  # "INBOUND" | "OUTBOUND"
    amount: float
    blockchain: str = field(default="")
    tx_hash: str | None = None
    from_address: str | None = None
    timestamp: str | None = None


@dataclass
class DepositInstructions:
    wallet_id: str
    address: str
    blockchain: str
    currency: str
    instructions: str


class PaymentGateway(ABC):
    """
    Abstract payment gateway.

    All marketplace payment operations (wallet creation, transfers, balance
    queries) go through this interface.  Swap implementations at will
    (Circle, Stripe, on-chain, etc.) without touching any service code.
    """

    # ── Wallets ────────────────────────────────────────────────────────────────

    @abstractmethod
    async def create_wallet(
        self,
        name: str,
        blockchain: str | None = None,
    ) -> WalletInfo: ...

    @abstractmethod
    async def get_wallet(self, wallet_id: str) -> WalletInfo: ...

    @abstractmethod
    async def get_balance(self, wallet_id: str) -> float:
        """Return USDC balance as a float.  Returns 0.0 when wallet holds no USDC."""
        ...

    @abstractmethod
    async def get_deposit_instructions(self, wallet_id: str) -> DepositInstructions: ...

    # ── Transfers ──────────────────────────────────────────────────────────────

    @abstractmethod
    async def create_transfer(
        self,
        from_wallet_id: str,
        to_address: str,
        amount: float,
        blockchain: str | None = None,
        idempotency_key: str | None = None,
    ) -> TransferResult: ...

    @abstractmethod
    async def get_transfer(self, transfer_id: str) -> TransferResult: ...

    @abstractmethod
    async def wait_for_transfer(
        self,
        transfer_id: str,
        max_wait_seconds: int = 120,
    ) -> TransferResult: ...

    # ── Transactions ───────────────────────────────────────────────────────────

    @abstractmethod
    async def get_wallet_transactions(
        self,
        wallet_id: str,
        page_size: int = 10,
    ) -> list[TransactionInfo]: ...

    # ── Wallet sets ────────────────────────────────────────────────────────────

    @abstractmethod
    async def create_wallet_set(self, name: str) -> dict[str, Any]: ...

    # ── Utility (provider-agnostic) ────────────────────────────────────────────

    @staticmethod
    def get_explorer_url(tx_hash: str, blockchain: str) -> str:
        """Return a block-explorer URL for the given transaction hash."""
        base = _EXPLORER_URLS.get(blockchain, "")
        if not base or not tx_hash:
            return ""
        return f"{base}{tx_hash}"


@lru_cache(maxsize=1)
def get_payment_gateway() -> PaymentGateway:
    """
    Application-level factory.
    Returns the configured payment gateway singleton (Circle by default).
    Replace the body to swap payment providers without touching callers.
    """
    from app.services.circle_client import CircleClient  # noqa: PLC0415

    return CircleClient()
