from __future__ import annotations

import asyncio
import base64
import logging
import uuid
from decimal import Decimal
from typing import Any

import aiohttp

from app.core.config import settings

logger = logging.getLogger(__name__)

_TERMINAL_STATES = {"COMPLETE", "FAILED", "CANCELLED"}

_EXPLORER_URLS: dict[str, str] = {
    "ARC-TESTNET": "https://explorer.arcana.network/tx/",
    "ETH-SEPOLIA": "https://sepolia.etherscan.io/tx/",
    "ETH": "https://etherscan.io/tx/",
    "ARB": "https://arbiscan.io/tx/",
    "MATIC-AMOY": "https://amoy.polygonscan.com/tx/",
    "MATIC": "https://polygonscan.com/tx/",
}


class CircleClient:
    """
    Async client for Circle Developer-Controlled Wallets API.
    Entity secret is loaded from settings and never logged.
    A fresh RSA-OAEP ciphertext is generated for every write request.
    """

    def __init__(self) -> None:
        self._base_url = settings.CIRCLE_BASE_URL.rstrip("/")
        self._api_key = settings.CIRCLE_API_KEY
        self._entity_secret_bytes = (
            bytes.fromhex(settings.CIRCLE_ENTITY_SECRET) if settings.CIRCLE_ENTITY_SECRET else b""
        )
        self._public_key_pem: bytes | None = None  # fetched once, then cached

    # ─────────────────────────────────────────────────
    # Internal helpers
    # ─────────────────────────────────────────────────

    def _auth_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    async def _fetch_public_key(self) -> bytes:
        if self._public_key_pem is not None:
            return self._public_key_pem
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self._base_url}/v1/w3s/config/entity/publicKey",
                headers=self._auth_headers(),
            ) as resp:
                resp.raise_for_status()
                data: dict[str, Any] = await resp.json()
                pem: str = data["data"]["publicKey"]
                self._public_key_pem = pem.encode()
                return self._public_key_pem

    async def _fresh_ciphertext(self) -> str:
        """Encrypt the fixed entity secret under Circle's public key (RSA-OAEP/SHA-256)."""
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import padding

        pem = await self._fetch_public_key()
        public_key = serialization.load_pem_public_key(pem)
        ciphertext = public_key.encrypt(  # type: ignore[union-attr]
            self._entity_secret_bytes,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )
        return base64.b64encode(ciphertext).decode()

    # ─────────────────────────────────────────────────
    # Wallet sets
    # ─────────────────────────────────────────────────

    async def create_wallet_set(self, name: str) -> dict[str, Any]:
        body = {
            "idempotencyKey": str(uuid.uuid4()),
            "name": name,
            "entitySecretCiphertext": await self._fresh_ciphertext(),
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self._base_url}/v1/w3s/developer/walletSets",
                json=body,
                headers=self._auth_headers(),
            ) as resp:
                resp.raise_for_status()
                data: dict[str, Any] = await resp.json()
                return dict(data["data"]["walletSet"])

    # ─────────────────────────────────────────────────
    # Wallets
    # ─────────────────────────────────────────────────

    async def create_developer_wallet(
        self,
        wallet_set_id: str | None = None,
        blockchain: str | None = None,
        name: str = "Escrow Wallet",
    ) -> dict[str, Any]:
        """
        Create one developer-controlled escrow wallet.
        Returns the wallet dict from Circle (id, address, state, blockchain, ...).
        """
        body = {
            "idempotencyKey": str(uuid.uuid4()),
            "entitySecretCiphertext": await self._fresh_ciphertext(),
            "walletSetId": wallet_set_id or settings.CIRCLE_WALLET_SET_ID,
            "blockchains": [blockchain or settings.BLOCKCHAIN],
            "count": 1,
            "metadata": [{"name": name}],
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self._base_url}/v1/w3s/developer/wallets",
                json=body,
                headers=self._auth_headers(),
            ) as resp:
                resp.raise_for_status()
                data: dict[str, Any] = await resp.json()
                wallets: list[dict[str, Any]] = data["data"]["wallets"]
                return wallets[0]

    # ─────────────────────────────────────────────────
    # Balances
    # ─────────────────────────────────────────────────

    async def get_wallet_balance(self, wallet_id: str) -> float:
        """Return USDC balance as float. Returns 0.0 if wallet has no USDC."""
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self._base_url}/v1/w3s/wallets/{wallet_id}/balances",
                headers=self._auth_headers(),
            ) as resp:
                resp.raise_for_status()
                data: dict[str, Any] = await resp.json()
                balances: list[dict[str, Any]] = data["data"].get("tokenBalances", [])
                for entry in balances:
                    token = entry.get("token", {})
                    if token.get("symbol", "").upper() == "USDC":
                        return float(entry.get("amount", "0"))
                return 0.0

    async def get_wallet(self, wallet_id: str) -> dict[str, Any]:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self._base_url}/v1/w3s/wallets/{wallet_id}",
                headers=self._auth_headers(),
            ) as resp:
                resp.raise_for_status()
                data: dict[str, Any] = await resp.json()
                return dict(data["data"]["wallet"])

    async def get_deposit_instructions(self, wallet_id: str) -> dict[str, Any]:
        wallet = await self.get_wallet(wallet_id)
        address = str(wallet.get("address") or "")
        blockchain = str(wallet.get("blockchain") or settings.BLOCKCHAIN)
        return {
            "walletId": wallet_id,
            "address": address,
            "blockchain": blockchain,
            "currency": "USDC",
            "instructions": (
                f"Send USDC on {blockchain} to {address}. Only send supported USDC assets "
                "on the selected network."
            ),
        }

    # ─────────────────────────────────────────────────
    # Transactions
    # ─────────────────────────────────────────────────

    async def get_wallet_transactions(
        self, wallet_id: str, *, page_size: int = 10
    ) -> list[dict[str, Any]]:
        """Recent transactions for a wallet (newest first)."""
        params: dict[str, str] = {
            "walletIds": wallet_id,
            "pageSize": str(page_size),
            "order": "DESC",
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self._base_url}/v1/w3s/transactions",
                params=params,
                headers=self._auth_headers(),
            ) as resp:
                resp.raise_for_status()
                data: dict[str, Any] = await resp.json()
                return list(data["data"].get("transactions", []))

    async def get_transaction(self, transaction_id: str) -> dict[str, Any]:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self._base_url}/v1/w3s/transactions/{transaction_id}",
                headers=self._auth_headers(),
            ) as resp:
                resp.raise_for_status()
                data: dict[str, Any] = await resp.json()
                return dict(data["data"]["transaction"])

    async def create_transfer(
        self,
        from_wallet_id: str,
        to_address: str,
        amount: float,
        blockchain: str | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        """
        Transfer USDC from a developer-controlled wallet to any address.
        Circle expects amounts as an array of strings with 6 decimal places.
        """
        body: dict[str, Any] = {
            "idempotencyKey": idempotency_key or str(uuid.uuid4()),
            "entitySecretCiphertext": await self._fresh_ciphertext(),
            "walletId": from_wallet_id,
            "destinationAddress": to_address,
            "amounts": [f"{amount:.6f}"],
            "blockchain": blockchain or settings.BLOCKCHAIN,
            "feeLevel": "MEDIUM",
        }
        # Remove None values
        body = {k: v for k, v in body.items() if v is not None}

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self._base_url}/v1/w3s/developer/transactions/transfer",
                json=body,
                headers=self._auth_headers(),
            ) as resp:
                resp.raise_for_status()
                data: dict[str, Any] = await resp.json()
                return dict(data["data"]["transaction"])

    async def create_withdrawal(
        self,
        from_wallet_id: str,
        to_address: str,
        amount: Decimal,
        blockchain: str | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        return await self.create_transfer(
            from_wallet_id=from_wallet_id,
            to_address=to_address,
            amount=float(amount),
            blockchain=blockchain,
            idempotency_key=idempotency_key,
        )

    async def wait_for_transfer_completion(
        self, transaction_id: str, max_wait_seconds: int = 120
    ) -> dict[str, Any]:
        """Poll until terminal state (COMPLETE / FAILED / CANCELLED)."""
        elapsed = 0
        poll_interval = 3
        while elapsed < max_wait_seconds:
            tx = await self.get_transaction(transaction_id)
            if tx.get("state") in _TERMINAL_STATES:
                return tx
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval
        raise TimeoutError(
            f"Transaction {transaction_id} did not reach terminal state in {max_wait_seconds}s"
        )

    # ─────────────────────────────────────────────────
    # Explorer URL
    # ─────────────────────────────────────────────────

    @staticmethod
    def get_explorer_url(tx_hash: str, blockchain: str) -> str:
        base = _EXPLORER_URLS.get(blockchain, "")
        if not base or not tx_hash:
            return ""
        return f"{base}{tx_hash}"
