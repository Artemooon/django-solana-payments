from decimal import Decimal

from solana.rpc.types import TokenAccountOpts
from solders.pubkey import Pubkey

from django_solana_payments.solana.base_solana_client import BaseSolanaClient


class SolanaBalanceClient:
    def __init__(self, base_solana_client: BaseSolanaClient):
        self.base_solana_client = base_solana_client

    def get_balance_by_address(self, address: Pubkey) -> Decimal:
        balance = self.base_solana_client.http_client.get_balance(address).value
        return Decimal(balance) / Decimal(self.base_solana_client.LAMPORTS_PER_SOL)

    def get_spl_token_balance_by_address(
        self, address: Pubkey, token_mint_address: Pubkey
    ) -> Decimal:
        opts = TokenAccountOpts(mint=token_mint_address)
        response = self.base_solana_client.http_client.get_token_accounts_by_owner(
            address, opts
        )
        if not response.value:
            return Decimal("0")
        token_account = response.value[0].pubkey
        balance_response = (
            self.base_solana_client.http_client.get_token_account_balance(
                Pubkey(token_account.__bytes__())
            )
        )

        return Decimal(balance_response.value.amount) / Decimal(
            10**balance_response.value.decimals
        )
