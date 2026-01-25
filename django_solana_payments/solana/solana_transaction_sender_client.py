import logging
from decimal import Decimal

import httpx
import stamina
from solana.exceptions import SolanaRpcException
from solders.keypair import Keypair
from solders.pubkey import Pubkey

from django_solana_payments.solana.base_solana_client import BaseSolanaClient
from django_solana_payments.solana.dtos import ConfirmTransactionDTO
from django_solana_payments.solana.enums import TransactionTypeEnum
from django_solana_payments.solana.solana_transaction_builder import SolanaTransactionBuilder

solana_client_logger = logging.getLogger(__name__)


class SolanaTransactionSenderClient:
    def __init__(self, base_solana_client: BaseSolanaClient, solana_transaction_builder: SolanaTransactionBuilder):
        self.base_solana_client = base_solana_client
        self.solana_transaction_builder = solana_transaction_builder

    def send_transfer_transaction(
        self, recipient: Pubkey,
            amount: Decimal,
            transaction_type: TransactionTypeEnum,
            sender_keypair: Keypair = None,
            token_mint_address: Pubkey = None
    ) -> ConfirmTransactionDTO | None:
        # Hard check for the transaction type
        assert transaction_type and isinstance(transaction_type, TransactionTypeEnum)

        sender_keypair = sender_keypair or self.base_solana_client.BASE_SENDER_KEYPAIR
        if not sender_keypair:
            return None

        if transaction_type == TransactionTypeEnum.NATIVE:
            transaction = self.solana_transaction_builder.create_native_transaction(
                recipient=recipient,
                amount=amount,
                sender_keypair=sender_keypair,
            )

        elif transaction_type == TransactionTypeEnum.SPL:
            if not token_mint_address:
                raise ValueError("token_mint_address is required for SPL token transfers")

            transaction = self.solana_transaction_builder.create_spl_token_transaction(
                recipient=recipient,
                amount=amount,
                sender_keypair=sender_keypair,
                token_mint_address=token_mint_address,
            )

        else:
            raise NotImplementedError(f"Unsupported transaction type: {transaction_type}")

        sent_transaction_signature = self.base_solana_client.send_transaction_with_retry(transaction)

        solana_client_logger.info(f"Transaction was sent to the: {str(recipient)}")
        return self.base_solana_client.confirm_transaction(sent_transaction_signature)
