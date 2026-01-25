import logging
from typing import Optional

from solana.rpc.commitment import Commitment
from solders.pubkey import Pubkey
from solders.signature import Signature
from solders.solders import GetTransactionResp
from solders.transaction_status import TransactionStatus

from django_solana_payments.settings import solana_payments_settings
from django_solana_payments.solana.base_solana_client import BaseSolanaClient

logger = logging.getLogger(__name__)


class SolanaTransactionQueryClient:

    def __init__(self, base_solana_client: BaseSolanaClient):
        self.base_solana_client = base_solana_client

    def get_signatures_statuses(
        self,
        signatures: list[Signature],
    ) -> list[Optional[TransactionStatus]]:
        response = self.base_solana_client.http_client.get_signature_statuses(
            signatures, search_transaction_history=True
        )
        return response.value

    def get_transactions_for_address(
        self,
        address: Pubkey,
        limit: Optional[int] = 2,
        commitment: Commitment = solana_payments_settings.RPC_CALLS_COMMITMENT,
    ) -> list[GetTransactionResp]:
        tx_signatures = self.base_solana_client.http_client.get_signatures_for_address(
            address, limit=limit, commitment=commitment
        ).value
        transactions = [
            self.base_solana_client.http_client.get_transaction(
                tx.signature, commitment=commitment
            )
            for tx in tx_signatures
        ]
        return transactions

    def extract_fee_payer_from_transaction_details(
        self, transaction_details
    ) -> Pubkey | None:
        tx_result = transaction_details.value.transaction.transaction

        if tx_result:
            fee_payer = tx_result.message.account_keys[0]

            return fee_payer

        return None
