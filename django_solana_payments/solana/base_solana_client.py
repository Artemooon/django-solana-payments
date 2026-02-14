import logging

import httpx
import stamina
from solana.exceptions import SolanaRpcException
from solana.rpc.api import Client
from solana.rpc.commitment import Commitment
from solders.keypair import Keypair
from solders.signature import Signature
from solders.solders import Transaction
from spl.token.constants import NATIVE_DECIMALS

from django_solana_payments.settings import solana_payments_settings
from django_solana_payments.solana.dtos import ConfirmTransactionDTO
from django_solana_payments.solana.utils import parse_keypair

solana_client_logger = logging.getLogger(__name__)


class BaseSolanaClient:

    def __init__(self, rpc_url: str = None):
        self._rpc_url = self._build_rpc_url(rpc_url)
        self._http_client = Client(
            endpoint=self._rpc_url,
            commitment=solana_payments_settings.RPC_COMMITMENT,
        )
        self.LAMPORTS_PER_SOL = 10**NATIVE_DECIMALS

    @staticmethod
    def _build_rpc_url(rpc_url: str | None) -> str:
        """Builds Solana RPC endpoint URL with provided rpc_url parameter if needed."""
        final_url = rpc_url or solana_payments_settings.RPC_URL

        return final_url

    @property
    def BASE_SENDER_KEYPAIR(self) -> Keypair:
        """
        Parse keypair from settings. Supports multiple formats:
        - JSON string: "[1,2,3,...,64]"
        - Base58 string: "5J3mBbAH58CpQ3Y2S4t7f..."
        - Byte array: [1,2,3,...,64]
        """
        keypair_data = solana_payments_settings.FEE_PAYER_KEYPAIR

        try:
            return parse_keypair(keypair_data)
        except (ValueError, AttributeError, TypeError) as e:
            solana_client_logger.error(f"Invalid FEE_PAYER_KEYPAIR: {e}")
            raise ValueError(
                "Invalid FEE_PAYER_KEYPAIR in settings. "
                "Supported formats: JSON string '[1,2,3,...]', Base58 string, or byte array. "
                f"Error: {e}"
            )

    @property
    def http_client(self):
        return self._http_client

    def generate_keypair(self) -> Keypair:
        return Keypair()

    def confirm_transaction(
        self,
        tx_signature: Signature,
        commitment: Commitment = solana_payments_settings.RPC_COMMITMENT,
    ) -> ConfirmTransactionDTO | None:
        if commitment is None:
            commitment = solana_payments_settings.RPC_COMMITMENT

        transaction_confirmation = self.http_client.confirm_transaction(
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

    @stamina.retry(
        on=(SolanaRpcException, httpx.HTTPStatusError, httpx.RequestError),
        attempts=5,
        wait_initial=1.0,
        wait_max=5.0,
    )
    def send_transaction_with_retry(self, transaction: Transaction) -> Signature:
        """
        Sends a transaction with retries on network errors.
        """
        try:
            sent_transaction = self.http_client.send_transaction(transaction)
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


base_solana_client = BaseSolanaClient()
