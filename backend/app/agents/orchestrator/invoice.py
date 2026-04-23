import json
from web3 import AsyncWeb3
from typing import Optional
from app.core.config import settings
from loguru import logger


class InvoiceService:

    def __init__(self):
        self.w3               = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider(settings.RPC_URL))
        self.contract_address = settings.INVOICE_CONTRACT_ADDRESS
        self.contract         = self.w3.eth.contract(
            address=self.contract_address,
            abi=settings.INVOICE_CONTRACT_ABI
        )
        self.orchestrator_account = self.w3.eth.account.from_key(
            settings.ORCHESTRATOR_PRIVATE_KEY
        )

    async def create_invoice(
        self,
        session_id:    str,
        payer_address: str,
        payee_address: str,
        amount:        float,
        description:   str
    ) -> Optional[dict]:
        try:
            # Convert USDC amount to 6 decimal integer
            amount_raw = int(amount * 1_000_000)

            tx = await self.contract.functions.createInvoice(
                session_id,
                payer_address,
                payee_address,
                amount_raw,
                description
            ).transact({
                "from": self.orchestrator_account.address,
                "gas":  300_000
            })

            receipt = await self.w3.eth.wait_for_transaction_receipt(tx)

            # Decode InvoiceCreated event to get invoiceId
            events = self.contract.events.InvoiceCreated().process_receipt(receipt)
            invoice_id = events[0]["args"]["invoiceId"].hex()

            return {
                "invoice_id":       invoice_id,
                "contract_address": self.contract_address,
                "tx_hash":          tx.hex()
            }
        except Exception as e:
            logger.error(f"Invoice creation failed: {e}")
            return None

    async def verify_payment(self, invoice_id: str) -> bool:
        try:
            invoice_id_bytes = bytes.fromhex(invoice_id)
            return await self.contract.functions.isInvoicePaid(
                invoice_id_bytes
            ).call()
        except Exception as e:
            logger.error(f"Payment verification failed: {e}")
            return False

    async def disburse_session_invoices(self, session_id: str) -> bool:
        try:
            tx = await self.contract.functions.disburseSessionInvoices(
                session_id
            ).transact({
                "from": self.orchestrator_account.address,
                "gas":  500_000
            })
            await self.w3.eth.wait_for_transaction_receipt(tx)
            return True
        except Exception as e:
            logger.error(f"Disbursement failed: {e}")
            return False