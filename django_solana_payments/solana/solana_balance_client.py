from decimal import Decimal

from solana.rpc.commitment import Commitment
from solana.rpc.models import TokenAccountOpts
from solders.pubkey import Pubkey

from django_solana_payments.settings import solana_payments_settings
from django_solana_payments.solana.base_solana_client import BaseSolanaClient


class SolanaBalanceClient:
    def __init__(self, base_solana_client: BaseSolanaClient):
        self.base_solana_client = base_solana_client

    async def aget_balance(self, address, commitment: Commitment | None = None):
        if commitment is None:
            commitment = solana_payments_settings.RPC_COMMITMENT
        async with self.base_solana_client.http_client() as client:
            return await client.get_balance(
                address,
                commitment=commitment,
            )

    def get_balance(self, address, commitment: Commitment | None = None):
        return self.base_solana_client.run_sync_from_async(
            self.aget_balance,
            address,
            commitment=commitment,
        )

    async def aget_token_accounts_by_owner(
        self, address, opts, commitment: Commitment | None = None
    ):
        if commitment is None:
            commitment = solana_payments_settings.RPC_COMMITMENT
        async with self.base_solana_client.http_client() as client:
            return await client.get_token_accounts_by_owner(
                address,
                opts,
                commitment=commitment,
            )

    def get_token_accounts_by_owner(
        self, address, opts, commitment: Commitment | None = None
    ):
        return self.base_solana_client.run_sync_from_async(
            self.aget_token_accounts_by_owner,
            address,
            opts,
            commitment=commitment,
        )

    async def aget_token_account_balance(
        self, address, commitment: Commitment | None = None
    ):
        if commitment is None:
            commitment = solana_payments_settings.RPC_COMMITMENT
        async with self.base_solana_client.http_client() as client:
            return await client.get_token_account_balance(
                address,
                commitment=commitment,
            )

    def get_token_account_balance(self, address, commitment: Commitment | None = None):
        return self.base_solana_client.run_sync_from_async(
            self.aget_token_account_balance,
            address,
            commitment=commitment,
        )

    def get_balance_by_address(self, address: Pubkey) -> Decimal:
        balance = self.get_balance(address).value
        return Decimal(balance) / Decimal(self.base_solana_client.LAMPORTS_PER_SOL)

    def get_spl_token_balance_by_address(
        self, address: Pubkey, token_mint_address: Pubkey
    ) -> Decimal:
        opts = TokenAccountOpts(mint=token_mint_address)
        response = self.get_token_accounts_by_owner(address, opts)
        if not response.value:
            return Decimal("0")
        token_account = response.value[0].pubkey
        balance_response = self.get_token_account_balance(
            Pubkey(token_account.__bytes__())
        )

        return Decimal(balance_response.value.amount) / Decimal(
            10**balance_response.value.decimals
        )
