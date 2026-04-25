from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.api.routes.agents import get_active_user
from app.models.users import User
from app.models.wallets import TransactionStatus, TransactionType, WalletTransaction
from app.services.wallet_service import (
    InsufficientBalanceError,
    WalletProvisionError,
    WalletService,
    WalletServiceError,
    WalletTransactionNotFoundError,
)

router = APIRouter(prefix="/wallet", tags=["wallet"])


class APIModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


class PaginationMeta(APIModel):
    total: int
    page: int
    page_size: int = Field(alias="pageSize")
    has_next: bool = Field(alias="hasNext")


class BalanceResponse(APIModel):
    balance: Decimal
    currency: str = "USDC"
    source: str = "circle"


class WalletAddressResponse(APIModel):
    wallet_id: str = Field(alias="walletId")
    address: str
    blockchain: str
    qr_data: str = Field(alias="qrData")


class DepositRequest(APIModel):
    amount: Decimal | None = Field(default=None, gt=0)


class DepositResponse(APIModel):
    wallet_id: str = Field(alias="walletId")
    address: str
    blockchain: str
    currency: str
    instructions: str


class WithdrawRequest(APIModel):
    amount: Decimal = Field(gt=0)
    to_address: str = Field(min_length=1, alias="toAddress")
    blockchain: str | None = None


class WalletTransactionRead(APIModel):
    id: UUID
    transaction_type: TransactionType = Field(alias="transactionType")
    direction: str
    amount: Decimal
    signed_amount: Decimal = Field(alias="signedAmount")
    currency: str
    status: TransactionStatus
    circle_transfer_id: str | None = Field(alias="circleTransferId")
    onchain_tx_hash: str | None = Field(alias="onchainTxHash")
    from_address: str | None = Field(alias="fromAddress")
    to_address: str | None = Field(alias="toAddress")
    description: str | None
    metadata: dict[str, Any] = Field(alias="txMetadata")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")


class TransactionListResponse(APIModel):
    items: list[WalletTransactionRead]
    meta: PaginationMeta


class EarningsResponse(APIModel):
    total_earned: Decimal = Field(alias="totalEarned")
    items: list[WalletTransactionRead]
    meta: PaginationMeta


class EscrowItem(APIModel):
    invoice_id: UUID = Field(alias="invoiceId")
    job_id: UUID = Field(alias="jobId")
    agent_id: UUID = Field(alias="agentId")
    agent_name: str | None = Field(alias="agentName")
    locked_amount: Decimal = Field(alias="lockedAmount")
    currency: str
    status: str
    created_at: datetime = Field(alias="createdAt")


def serialize_transaction(tx: WalletTransaction) -> WalletTransactionRead:
    direction = (
        "inbound"
        if tx.transaction_type
        in {TransactionType.DEPOSIT, TransactionType.EARNING, TransactionType.REFUND}
        else "outbound"
    )
    signed_amount = tx.amount if direction == "inbound" else -tx.amount
    return WalletTransactionRead(
        id=tx.id,
        transactionType=tx.transaction_type,
        direction=direction,
        amount=tx.amount,
        signedAmount=signed_amount,
        currency=tx.currency,
        status=tx.status,
        circleTransferId=tx.circle_transfer_id,
        onchainTxHash=tx.onchain_tx_hash,
        fromAddress=tx.from_address,
        toAddress=tx.to_address,
        description=tx.description,
        txMetadata=tx.tx_metadata,
        createdAt=tx.created_at,
        updatedAt=tx.updated_at,
    )


def map_wallet_error(exc: Exception) -> HTTPException:
    if isinstance(exc, WalletTransactionNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(exc, InsufficientBalanceError):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    if isinstance(exc, WalletProvisionError):
        return HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))
    if isinstance(exc, WalletServiceError):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Wallet operation failed."
    )


@router.get("/balance", response_model=BalanceResponse)
async def get_wallet_balance(
    current_user: User = Depends(get_active_user),
    db: AsyncSession = Depends(get_session),
) -> BalanceResponse:
    try:
        balance = await WalletService(db).get_live_balance(current_user)
        return BalanceResponse(balance=balance)
    except Exception as exc:
        raise map_wallet_error(exc) from exc


@router.get("/address", response_model=WalletAddressResponse)
async def get_wallet_address(
    current_user: User = Depends(get_active_user),
    db: AsyncSession = Depends(get_session),
) -> WalletAddressResponse:
    try:
        payload = await WalletService(db).get_wallet_address(current_user)
        return WalletAddressResponse.model_validate(payload)
    except Exception as exc:
        raise map_wallet_error(exc) from exc


@router.post("/deposit", response_model=DepositResponse)
async def initiate_wallet_deposit(
    payload: DepositRequest | None = None,
    current_user: User = Depends(get_active_user),
    db: AsyncSession = Depends(get_session),
) -> DepositResponse:
    del payload
    try:
        instructions = await WalletService(db).initiate_deposit(current_user)
        return DepositResponse.model_validate(instructions)
    except Exception as exc:
        raise map_wallet_error(exc) from exc


@router.post(
    "/withdraw", response_model=WalletTransactionRead, status_code=status.HTTP_202_ACCEPTED
)
async def initiate_wallet_withdrawal(
    payload: WithdrawRequest,
    current_user: User = Depends(get_active_user),
    db: AsyncSession = Depends(get_session),
) -> WalletTransactionRead:
    try:
        tx = await WalletService(db).initiate_withdrawal(
            current_user,
            to_address=payload.to_address,
            amount=payload.amount,
            blockchain=payload.blockchain,
        )
        return serialize_transaction(tx)
    except Exception as exc:
        raise map_wallet_error(exc) from exc


@router.get("/transactions", response_model=TransactionListResponse)
async def list_wallet_transactions(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    transaction_type: TransactionType | None = Query(default=None, alias="type"),
    current_user: User = Depends(get_active_user),
    db: AsyncSession = Depends(get_session),
) -> TransactionListResponse:
    result = await WalletService(db).list_transactions(
        current_user,
        page=page,
        page_size=page_size,
        transaction_type=transaction_type,
    )
    return TransactionListResponse(
        items=[serialize_transaction(tx) for tx in result.transactions],
        meta=PaginationMeta(
            total=result.meta.total,
            page=result.meta.page,
            pageSize=result.meta.page_size,
            hasNext=result.meta.has_next,
        ),
    )


@router.get("/transactions/{tx_id}", response_model=WalletTransactionRead)
async def get_wallet_transaction(
    tx_id: UUID,
    current_user: User = Depends(get_active_user),
    db: AsyncSession = Depends(get_session),
) -> WalletTransactionRead:
    try:
        tx = await WalletService(db).get_transaction(current_user, tx_id)
        return serialize_transaction(tx)
    except Exception as exc:
        raise map_wallet_error(exc) from exc


@router.get("/earnings", response_model=EarningsResponse)
async def get_wallet_earnings(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_active_user),
    db: AsyncSession = Depends(get_session),
) -> EarningsResponse:
    result = await WalletService(db).get_earnings(current_user, page=page, page_size=page_size)
    meta = result["meta"]
    return EarningsResponse(
        totalEarned=result["totalEarned"],
        items=[serialize_transaction(tx) for tx in result["transactions"]],
        meta=PaginationMeta(
            total=meta.total,
            page=meta.page,
            pageSize=meta.page_size,
            hasNext=meta.has_next,
        ),
    )


@router.get("/escrow", response_model=list[EscrowItem])
async def get_active_wallet_escrow(
    current_user: User = Depends(get_active_user),
    db: AsyncSession = Depends(get_session),
) -> list[EscrowItem]:
    items = await WalletService(db).get_active_escrow(current_user)
    return [EscrowItem.model_validate(item) for item in items]
