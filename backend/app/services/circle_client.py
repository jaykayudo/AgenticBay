from __future__ import annotations

import asyncio
import logging
import uuid
from decimal import Decimal
from typing import Any

from app.core.config import settings
from app.services.payment_gateway import (
    DepositInstructions,
    PaymentGateway,
    TransactionInfo,
    TransferResult,
    WalletInfo,
)

logger = logging.getLogger(__name__)

_TERMINAL_STATES = {"COMPLETE", "FAILED", "CANCELLED"}


def _build_api_client() -> Any:
    """
    Build and return a Circle Developer-Controlled Wallets ApiClient.
    The public key is loaded from settings if available; otherwise fetched
    once from Circle's configuration endpoint (synchronous, happens at startup).
    """
    from circle.web3.developer_controlled_wallets.api_client import ApiClient
    from circle.web3.developer_controlled_wallets.configuration import Configuration

    public_key = settings.CIRCLE_PUBLIC_KEY or _fetch_public_key_sync()

    config = Configuration(  # type: ignore[no-untyped-call]
        host=settings.CIRCLE_BASE_URL,
        access_token=settings.CIRCLE_API_KEY or None,
        entity_secret=settings.CIRCLE_ENTITY_SECRET or None,
        public_key=public_key or None,
    )
    return ApiClient(configuration=config)  # type: ignore[no-untyped-call]


def _fetch_public_key_sync() -> str:
    """
    Fetch Circle's RSA public key from their configuration endpoint.
    Called once at startup when CIRCLE_PUBLIC_KEY is not set in env.
    """
    if not settings.CIRCLE_API_KEY:
        return ""
    try:
        from circle.web3.configurations.api.developer_account_api import DeveloperAccountApi
        from circle.web3.configurations.api_client import ApiClient as CfgApiClient
        from circle.web3.configurations.configuration import Configuration as CfgConfiguration

        cfg = CfgConfiguration(  # type: ignore[no-untyped-call]
            host=settings.CIRCLE_BASE_URL,
            access_token=settings.CIRCLE_API_KEY,
        )
        client = CfgApiClient(configuration=cfg)  # type: ignore[no-untyped-call]
        result = DeveloperAccountApi(client).get_public_key()  # type: ignore[no-untyped-call]
        pem: str = str(result.data.public_key or "")
        logger.info("Fetched Circle public key from API (%d chars)", len(pem))
        return pem
    except Exception:
        logger.warning("Could not fetch Circle public key; write operations will fail", exc_info=True)
        return ""


class CircleClient(PaymentGateway):
    """
    Circle Developer-Controlled Wallets implementation of PaymentGateway.

    Uses the official `circle-developer-controlled-wallets` SDK.
    SDK calls are synchronous (urllib3-backed); every call is wrapped in
    `asyncio.to_thread()` so it does not block the FastAPI event loop.
    """

    def __init__(self) -> None:
        self._api_client = _build_api_client()

        from circle.web3.developer_controlled_wallets.api.transactions_api import TransactionsApi
        from circle.web3.developer_controlled_wallets.api.wallet_sets_api import WalletSetsApi
        from circle.web3.developer_controlled_wallets.api.wallets_api import WalletsApi

        self._wallets: WalletsApi = WalletsApi(self._api_client)  # type: ignore[no-untyped-call]
        self._transactions: TransactionsApi = TransactionsApi(self._api_client)  # type: ignore[no-untyped-call]
        self._wallet_sets: WalletSetsApi = WalletSetsApi(self._api_client)  # type: ignore[no-untyped-call]

    # ── Wallets ────────────────────────────────────────────────────────────────

    async def create_wallet(
        self,
        name: str = "Wallet",
        blockchain: str | None = None,
    ) -> WalletInfo:
        from circle.web3.developer_controlled_wallets.models import (  # type: ignore[attr-defined]
            CreateWalletRequest,
            WalletMetadata,
        )

        req = CreateWalletRequest(  # type: ignore[no-untyped-call]
            blockchains=[blockchain or settings.BLOCKCHAIN],
            count=1,
            wallet_set_id=settings.CIRCLE_WALLET_SET_ID,
            metadata=[WalletMetadata(name=name)],  # type: ignore[no-untyped-call]
        )
        result = await asyncio.to_thread(self._wallets.create_wallet, req)
        wallet = result.data.wallets[0]
        return WalletInfo(
            wallet_id=str(wallet.id),
            address=str(wallet.address or ""),
            blockchain=str(wallet.blockchain.value if wallet.blockchain else settings.BLOCKCHAIN),
            state=str(wallet.state.value if wallet.state else "LIVE"),
        )

    async def get_wallet(self, wallet_id: str) -> WalletInfo:
        result = await asyncio.to_thread(self._wallets.get_wallet, wallet_id)
        wallet = result.data.wallet
        return WalletInfo(
            wallet_id=str(wallet.id),
            address=str(wallet.address or ""),
            blockchain=str(wallet.blockchain.value if wallet.blockchain else settings.BLOCKCHAIN),
            state=str(wallet.state.value if wallet.state else "LIVE"),
        )

    async def get_balance(self, wallet_id: str) -> float:
        """Return the USDC balance as a float.  Returns 0.0 if wallet holds no USDC."""
        result = await asyncio.to_thread(self._wallets.list_wallet_balance, wallet_id)
        for entry in result.data.token_balances or []:
            token = entry.token
            if token and token.symbol and token.symbol.upper() == "USDC":
                return float(str(entry.amount))
        return 0.0

    async def get_deposit_instructions(self, wallet_id: str) -> DepositInstructions:
        info = await self.get_wallet(wallet_id)
        blockchain = info.blockchain or settings.BLOCKCHAIN
        return DepositInstructions(
            wallet_id=wallet_id,
            address=info.address,
            blockchain=blockchain,
            currency="USDC",
            instructions=(
                f"Send USDC on {blockchain} to {info.address}. "
                "Only send supported USDC assets on the selected network."
            ),
        )

    # ── Transfers ──────────────────────────────────────────────────────────────

    async def create_transfer(
        self,
        from_wallet_id: str,
        to_address: str,
        amount: float,
        blockchain: str | None = None,
        idempotency_key: str | None = None,
    ) -> TransferResult:
        from circle.web3.developer_controlled_wallets.models import (  # type: ignore[attr-defined]
            CreateTransferTransactionForDeveloperRequest,
            FeeLevel,
        )

        req = CreateTransferTransactionForDeveloperRequest(  # type: ignore[no-untyped-call]
            wallet_id=from_wallet_id,
            destination_address=to_address,
            amounts=[f"{amount:.6f}"],
            fee_level=FeeLevel.MEDIUM,
            idempotency_key=idempotency_key or str(uuid.uuid4()),
            blockchain=blockchain or settings.BLOCKCHAIN,
        )
        result = await asyncio.to_thread(
            self._transactions.create_developer_transaction_transfer, req
        )
        tx = result.data.transaction
        return TransferResult(
            transfer_id=str(tx.id),
            state=str(tx.state.value if tx.state else "PENDING"),
            tx_hash=tx.tx_hash or None,
        )

    async def get_transfer(self, transfer_id: str) -> TransferResult:
        result = await asyncio.to_thread(self._transactions.get_transaction, transfer_id)
        tx = result.data.transaction
        return TransferResult(
            transfer_id=str(tx.id),
            state=str(tx.state.value if tx.state else "PENDING"),
            tx_hash=tx.tx_hash or None,
        )

    async def wait_for_transfer(
        self,
        transfer_id: str,
        max_wait_seconds: int = 120,
    ) -> TransferResult:
        elapsed = 0
        poll_interval = 3
        while elapsed < max_wait_seconds:
            result = await self.get_transfer(transfer_id)
            if result.state in _TERMINAL_STATES:
                return result
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval
        raise TimeoutError(
            f"Transaction {transfer_id} did not reach terminal state in {max_wait_seconds}s"
        )

    # ── Transactions ───────────────────────────────────────────────────────────

    async def get_wallet_transactions(
        self,
        wallet_id: str,
        page_size: int = 10,
    ) -> list[TransactionInfo]:
        result = await asyncio.to_thread(
            self._transactions.list_transactions,
            wallet_ids=wallet_id,
            page_size=page_size,
            order="DESC",
        )
        out: list[TransactionInfo] = []
        for tx in result.data.transactions or []:
            tx_type = str(tx.transaction_type.value if tx.transaction_type else "")
            direction = "INBOUND" if tx_type == "INBOUND" else "OUTBOUND"
            amount = 0.0
            if tx.amounts:
                try:
                    amount = float(tx.amounts[0])
                except (ValueError, IndexError):
                    pass
            out.append(
                TransactionInfo(
                    transaction_id=str(tx.id),
                    direction=direction,
                    amount=amount,
                    blockchain=str(tx.blockchain.value if tx.blockchain else settings.BLOCKCHAIN),
                    tx_hash=tx.tx_hash or None,
                    from_address=tx.source_address or None,
                    timestamp=tx.update_date.isoformat() if tx.update_date else None,
                )
            )
        return out

    # ── Wallet sets ────────────────────────────────────────────────────────────

    async def create_wallet_set(self, name: str) -> dict[str, Any]:
        from circle.web3.developer_controlled_wallets.models import (  # type: ignore[attr-defined]
            CreateWalletSetRequest,
        )

        req = CreateWalletSetRequest(name=name)  # type: ignore[no-untyped-call]
        result = await asyncio.to_thread(self._wallet_sets.create_wallet_set, req)
        ws = result.data.wallet_set
        return {"id": str(ws.id), "name": str(ws.name or "")}

    # ── Backward-compatible helpers ────────────────────────────────────────────
    # These preserve the old CircleClient dict-based API so callers that have
    # not yet been migrated to PaymentGateway keep working.

    async def create_developer_wallet(
        self,
        wallet_set_id: str | None = None,
        blockchain: str | None = None,
        name: str = "Escrow Wallet",
    ) -> dict[str, Any]:
        info = await self.create_wallet(name=name, blockchain=blockchain)
        return {"id": info.wallet_id, "address": info.address}

    async def get_wallet_balance(self, wallet_id: str) -> float:
        return await self.get_balance(wallet_id)

    async def create_withdrawal(
        self,
        from_wallet_id: str,
        to_address: str,
        amount: Decimal,
        blockchain: str | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        result = await self.create_transfer(
            from_wallet_id=from_wallet_id,
            to_address=to_address,
            amount=float(amount),
            blockchain=blockchain,
            idempotency_key=idempotency_key,
        )
        return {"id": result.transfer_id, "state": result.state, "txHash": result.tx_hash}

    async def wait_for_transfer_completion(
        self,
        transaction_id: str,
        max_wait_seconds: int = 120,
    ) -> dict[str, Any]:
        result = await self.wait_for_transfer(transaction_id, max_wait_seconds)
        return {"id": result.transfer_id, "state": result.state, "txHash": result.tx_hash}
