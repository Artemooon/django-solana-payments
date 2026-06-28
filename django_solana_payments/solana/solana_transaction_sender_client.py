import logging
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

import httpx
import stamina
from solana.exceptions import SolanaRpcException
from solana.rpc.commitment import Commitment
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.signature import Signature
from solders.solders import VersionedTransaction

from django_solana_payments.settings import solana_payments_settings
from django_solana_payments.solana.base_solana_client import BaseSolanaClient
from django_solana_payments.solana.dtos import ConfirmTransactionDTO
from django_solana_payments.solana.enums import TransactionTypeEnum

if TYPE_CHECKING:
    from django_solana_payments.solana.solana_transaction_builder import (
        SolanaTransactionBuilder,
    )

solana_client_logger = logging.getLogger(__name__)


class SolanaTransactionSenderClient:
    def __init__(
        self,
        base_solana_client: BaseSolanaClient,
        solana_transaction_builder: Optional["SolanaTransactionBuilder"] = None,
    ):
        self.base_solana_client = base_solana_client
        self.solana_transaction_builder = solana_transaction_builder

    async def asend_transaction(self, transaction: VersionedTransaction):
        async with self.base_solana_client.http_client() as client:
            return await client.send_transaction(transaction)

    def send_transaction(self, transaction: VersionedTransaction):
        return self.base_solana_client.run_sync_from_async(
            self.asend_transaction,
            transaction,
        )

    async def aconfirm_transaction(
        self,
        tx_signature: Signature,
        commitment: Commitment = solana_payments_settings.RPC_COMMITMENT,
    ) -> ConfirmTransactionDTO | None:
        if commitment is None:
            commitment = solana_payments_settings.RPC_COMMITMENT

        async with self.base_solana_client.http_client() as client:
            transaction_confirmation = await client.confirm_transaction(
                tx_signature, commitment=commitment
            )
        transaction_confirmation_data = transaction_confirmation.value
        solana_client_logger.info(
            f"Transaction with signature: {str(tx_signature)} was confirmed"
        )

        if not transaction_confirmation_data:
            solana_client_logger.error(
                f"Transaction with signature: {str(tx_signature)} was not confirmed"
            )
            return ConfirmTransactionDTO(tx_signature=tx_signature)

        return ConfirmTransactionDTO(
            confirmation_status=transaction_confirmation.value[
                len(transaction_confirmation_data) - 1
            ].confirmation_status,
            tx_signature=tx_signature,
        )

    def confirm_transaction(
        self,
        tx_signature: Signature,
        commitment: Commitment = solana_payments_settings.RPC_COMMITMENT,
    ) -> ConfirmTransactionDTO | None:
        return self.base_solana_client.run_sync_from_async(
            self.aconfirm_transaction,
            tx_signature,
            commitment=commitment,
        )

    @stamina.retry(
        on=(SolanaRpcException, httpx.HTTPStatusError, httpx.RequestError),
        attempts=5,
        wait_initial=1.0,
        wait_max=5.0,
    )
    async def asend_transaction_with_retry(self, transaction: VersionedTransaction):
        try:
            sent_transaction = await self.asend_transaction(transaction)
            return sent_transaction.value
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                solana_client_logger.warning(
                    "Rate limit reached while sending transaction — will retry"
                )
            else:
                solana_client_logger.warning(f"send_transaction error: {str(e)}")
            raise
        except (SolanaRpcException, httpx.RequestError) as e:
            solana_client_logger.warning(f"send_transaction error: {e}")
            raise
        except Exception as e:
            solana_client_logger.error(f"An unexpected error occurred: {e}")
            raise

    @stamina.retry(
        on=(SolanaRpcException, httpx.HTTPStatusError, httpx.RequestError),
        attempts=5,
        wait_initial=1.0,
        wait_max=5.0,
    )
    def send_transaction_with_retry(self, transaction: VersionedTransaction):
        try:
            sent_transaction = self.send_transaction(transaction)
            return sent_transaction.value
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                solana_client_logger.warning(
                    "Rate limit reached while sending transaction — will retry"
                )
            else:
                solana_client_logger.warning(f"send_transaction error: {str(e)}")
            raise
        except (SolanaRpcException, httpx.RequestError) as e:
            solana_client_logger.warning(f"send_transaction error: {e}")
            raise
        except Exception as e:
            solana_client_logger.error(f"An unexpected error occurred: {e}")
            raise

    def send_transfer_transaction(
        self,
        recipient: Pubkey,
        amount: Decimal,
        transaction_type: TransactionTypeEnum,
        sender_keypair: Keypair = None,
        token_mint_address: Pubkey = None,
    ) -> ConfirmTransactionDTO | None:
        # Hard check for the transaction type
        assert transaction_type and isinstance(transaction_type, TransactionTypeEnum)
        if self.solana_transaction_builder is None:
            raise ValueError(
                "solana_transaction_builder is required for transfer transactions"
            )

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
                raise ValueError(
                    "token_mint_address is required for SPL token transfers"
                )

            transaction = self.solana_transaction_builder.create_spl_token_transaction(
                recipient=recipient,
                amount=amount,
                sender_keypair=sender_keypair,
                token_mint_address=token_mint_address,
            )

        else:
            raise NotImplementedError(
                f"Unsupported transaction type: {transaction_type}"
            )

        sent_transaction_signature = self.send_transaction_with_retry(transaction)

        solana_client_logger.info(f"Transaction was sent to the: {str(recipient)}")
        return self.confirm_transaction(sent_transaction_signature)
