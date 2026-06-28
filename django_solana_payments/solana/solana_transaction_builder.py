from decimal import Decimal
from typing import TYPE_CHECKING

from solders.instruction import Instruction
from solders.keypair import Keypair
from solders.message import MessageV0
from solders.pubkey import Pubkey
from solders.system_program import TransferParams, transfer
from solders.transaction import VersionedTransaction
from spl.token.instructions import transfer as spl_transfer
from spl.token.models import TransferParams as SplTransferParams

from django_solana_payments.solana.base_solana_client import BaseSolanaClient

if TYPE_CHECKING:
    from django_solana_payments.solana.solana_token_client import SolanaTokenClient


class SolanaTransactionBuilder:
    def __init__(
        self,
        base_solana_client: BaseSolanaClient,
        solana_token_client: "SolanaTokenClient",
    ):
        self.base_solana_client = base_solana_client
        self.solana_token_client = solana_token_client

    def _build_versioned_transaction(
        self,
        instructions: list[Instruction],
        signers: list[Keypair],
    ) -> VersionedTransaction:
        latest_blockhash = self.solana_token_client.get_latest_blockhash().value
        message = MessageV0.try_compile(
            payer=self.base_solana_client.BASE_SENDER_KEYPAIR.pubkey(),
            instructions=instructions,
            address_lookup_table_accounts=[],
            recent_blockhash=latest_blockhash.blockhash,
        )
        return VersionedTransaction(message, signers)

    def create_native_transaction(
        self, recipient: Pubkey, amount: Decimal, sender_keypair: Keypair
    ) -> VersionedTransaction:
        amount_lamports = round(self.base_solana_client.LAMPORTS_PER_SOL * amount)
        transfer_ix = transfer(
            TransferParams(
                from_pubkey=sender_keypair.pubkey(),
                to_pubkey=recipient,
                lamports=amount_lamports,
            )
        )
        return self._build_versioned_transaction(
            instructions=[transfer_ix],
            signers=[sender_keypair, self.base_solana_client.BASE_SENDER_KEYPAIR],
        )

    def _calculate_spl_transaction_amount(self, amount: Decimal, decimals: int) -> int:
        return int(amount * (10**decimals))

    def create_spl_token_transaction(
        self,
        recipient: Pubkey,
        amount: Decimal,
        sender_keypair: Keypair,
        token_mint_address: Pubkey,
    ) -> VersionedTransaction:
        sender_associated_token_addr = (
            self.solana_token_client.get_or_create_associated_token_address(
                sender_keypair.pubkey(), token_mint_address
            )
        )
        recipient_associated_token_addr = (
            self.solana_token_client.get_or_create_associated_token_address(
                recipient, token_mint_address
            )
        )

        token_account_info = self.solana_token_client.get_account_info(
            token_mint_address
        )

        if not token_account_info.value:
            raise ValueError(
                f"create_spl_token_transaction: Mint account {token_mint_address} not found or invalid"
            )

        token_program_id = token_account_info.value.owner

        decimals = self.solana_token_client.get_token_supply(
            token_mint_address
        ).value.decimals

        tokens_to_send_amount = self._calculate_spl_transaction_amount(amount, decimals)

        transfer_instruction = spl_transfer(
            SplTransferParams(
                program_id=token_program_id,
                source=sender_associated_token_addr,
                dest=recipient_associated_token_addr,
                owner=sender_keypair.pubkey(),
                amount=tokens_to_send_amount,
            )
        )
        return self._build_versioned_transaction(
            instructions=[transfer_instruction],
            signers=[sender_keypair, self.base_solana_client.BASE_SENDER_KEYPAIR],
        )
