import logging
from contextlib import asynccontextmanager

from asgiref.sync import async_to_sync
from solana.rpc.async_api import AsyncClient
from solders.keypair import Keypair
from spl.token.constants import NATIVE_DECIMALS

from django_solana_payments.settings import solana_payments_settings
from django_solana_payments.solana.utils import parse_keypair

solana_client_logger = logging.getLogger(__name__)


class BaseSolanaClient:

    def __init__(self, rpc_url: str = None, client_factory=None):
        self._rpc_url = self._build_rpc_url(rpc_url)
        self._client_factory = client_factory or self._default_client_factory
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

    def _default_client_factory(self) -> AsyncClient:
        return AsyncClient(
            endpoint=self._rpc_url,
            commitment=solana_payments_settings.RPC_COMMITMENT,
            timeout=solana_payments_settings.RPC_TIMEOUT,
            extra_headers=solana_payments_settings.RPC_EXTRA_HEADERS,
            proxy=solana_payments_settings.RPC_PROXY,
            rate_limit=solana_payments_settings.RPC_RATE_LIMIT,
        )

    @asynccontextmanager
    async def http_client(self):
        client = self._client_factory()
        try:
            yield client
        finally:
            await client.close()

    def run_sync_from_async(self, async_callable, *args, **kwargs):
        return async_to_sync(async_callable)(*args, **kwargs)

    def generate_keypair(self) -> Keypair:
        return Keypair()

    async def aclose(self):
        return None


base_solana_client = BaseSolanaClient()
