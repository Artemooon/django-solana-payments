import logging

from solana.rpc.commitment import Commitment
from solders.instruction import Instruction
from solders.keypair import Keypair
from solders.message import MessageV0
from solders.pubkey import Pubkey
from solders.signature import Signature
from solders.transaction import VersionedTransaction
from spl.token.constants import (
    ASSOCIATED_TOKEN_PROGRAM_ID,
    TOKEN_2022_PROGRAM_ID,
    TOKEN_PROGRAM_ID,
)
from spl.token.instructions import (
    close_account,
    create_associated_token_account,
)
from spl.token.models import CloseAccountParams

from django_solana_payments.settings import solana_payments_settings
from django_solana_payments.solana.base_solana_client import BaseSolanaClient
from django_solana_payments.solana.solana_transaction_sender_client import (
    SolanaTransactionSenderClient,
)

solana_client_logger = logging.getLogger(__name__)


class SolanaTokenClient:
    def __init__(self, base_solana_client: BaseSolanaClient):
        self.base_solana_client = base_solana_client
        self.solana_transaction_sender_client = SolanaTransactionSenderClient(
            base_solana_client=base_solana_client
        )

    def _build_versioned_transaction(
        self,
        instructions: list[Instruction],
        signers: list[Keypair],
        recent_blockhash,
    ) -> VersionedTransaction:
        message = MessageV0.try_compile(
            payer=self.base_solana_client.BASE_SENDER_KEYPAIR.pubkey(),
            instructions=instructions,
            address_lookup_table_accounts=[],
            recent_blockhash=recent_blockhash,
        )
        return VersionedTransaction(message, signers)

    async def aget_account_info(self, address, commitment: Commitment | None = None):
        if commitment is None:
            commitment = solana_payments_settings.RPC_COMMITMENT
        async with self.base_solana_client.http_client() as client:
            return await client.get_account_info(
                address,
                commitment=commitment,
            )

    def get_account_info(self, address, commitment: Commitment | None = None):
        return self.base_solana_client.run_sync_from_async(
            self.aget_account_info,
            address,
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

    async def aget_latest_blockhash(self, commitment: Commitment | None = None):
        if commitment is None:
            commitment = solana_payments_settings.RPC_COMMITMENT
        async with self.base_solana_client.http_client() as client:
            return await client.get_latest_blockhash(commitment=commitment)

    def get_latest_blockhash(self, commitment: Commitment | None = None):
        return self.base_solana_client.run_sync_from_async(
            self.aget_latest_blockhash,
            commitment=commitment,
        )

    async def aget_token_supply(self, address, commitment: Commitment | None = None):
        if commitment is None:
            commitment = solana_payments_settings.RPC_COMMITMENT
        async with self.base_solana_client.http_client() as client:
            return await client.get_token_supply(
                address,
                commitment=commitment,
            )

    def get_token_supply(self, address, commitment: Commitment | None = None):
        return self.base_solana_client.run_sync_from_async(
            self.aget_token_supply,
            address,
            commitment=commitment,
        )

    def get_or_create_associated_token_address(
        self, wallet_address: Pubkey, token_mint_address: Pubkey
    ) -> Pubkey:
        associated_token_address = self.get_associated_token_address(
            wallet_address, token_mint_address
        )

        token_account = self.get_account_info(associated_token_address)
        if not token_account.value:
            self.create_associated_token_addresses_for_mints(
                wallet_address, [token_mint_address]
            )

        return associated_token_address

    def get_associated_token_address(
        self,
        wallet_address: Pubkey,
        token_mint_address: Pubkey,
        commitment: Commitment = solana_payments_settings.RPC_COMMITMENT,
    ) -> Pubkey:
        mint_info = self.get_account_info(token_mint_address, commitment=commitment)
        if not mint_info.value:
            raise ValueError(f"Mint account {token_mint_address} does not exist")

        program_owner = mint_info.value.owner  # owner program of the mint account

        # The order of seeds passed to find_program_address matters and
        # must match what the Associated Token program expects
        seeds = [bytes(wallet_address), bytes(program_owner), bytes(token_mint_address)]

        associated_token_address, _ = Pubkey.find_program_address(
            seeds, ASSOCIATED_TOKEN_PROGRAM_ID
        )

        return associated_token_address

    def create_associated_token_addresses_for_mints(
        self,
        recipient: Pubkey,
        mints: list[Pubkey],
        commitment: Commitment = solana_payments_settings.RPC_COMMITMENT,
    ) -> Signature:
        """
        Creates and sends transactions to close all specified token accounts.
        """

        latest_blockhash = self.get_latest_blockhash(commitment=commitment).value

        instructions = []

        for mint in mints:
            mint_info = self.get_account_info(mint, commitment=commitment).value

            instructions.append(
                create_associated_token_account(
                    payer=self.base_solana_client.BASE_SENDER_KEYPAIR.pubkey(),
                    owner=recipient,
                    mint=mint,
                    token_program_id=mint_info.owner,
                )
            )

        transaction = self._build_versioned_transaction(
            instructions=instructions,
            signers=[self.base_solana_client.BASE_SENDER_KEYPAIR],
            recent_blockhash=latest_blockhash.blockhash,
        )
        sent_transaction_sig = (
            self.solana_transaction_sender_client.send_transaction_with_retry(
                transaction
            )
        )

        self.solana_transaction_sender_client.confirm_transaction(sent_transaction_sig)

        return sent_transaction_sig

    async def aclose_associated_token_accounts_and_recover_rent(
        self,
        account_owner: Keypair,
        accounts_to_close: list[Pubkey],
        destination_pubkey: Pubkey,
        ata_program_id: Pubkey | None = None,
        commitment: Commitment = solana_payments_settings.RPC_COMMITMENT,
    ) -> bool:
        """
        Creates and sends transactions to close all specified token accounts.
        """
        if not accounts_to_close:
            solana_client_logger.warning("No empty token accounts found to close.")
            return False

        instructions = []
        for account_to_close in accounts_to_close:
            account_balance = (
                await self.aget_balance(account_to_close, commitment=commitment)
            ).value
            if account_balance <= 0:
                solana_client_logger.info(
                    f"Account: {account_to_close} has an insufficient balance: {account_balance} SOL"
                )
                continue

            if ata_program_id not in [TOKEN_PROGRAM_ID, TOKEN_2022_PROGRAM_ID]:
                ata_program_id = TOKEN_PROGRAM_ID

            params = CloseAccountParams(
                account=account_to_close,
                dest=destination_pubkey,
                owner=account_owner.pubkey(),
                program_id=ata_program_id,
            )
            instructions.append(close_account(params))

        if not instructions:
            return False

        latest_blockhash = (
            await self.aget_latest_blockhash(commitment=commitment)
        ).value

        tx = self._build_versioned_transaction(
            instructions=instructions,
            signers=[account_owner, self.base_solana_client.BASE_SENDER_KEYPAIR],
            recent_blockhash=latest_blockhash.blockhash,
        )

        try:
            sent_transaction_sig = await self.solana_transaction_sender_client.asend_transaction_with_retry(
                tx
            )
            solana_client_logger.info(f"Transaction sent: {sent_transaction_sig}")
            # Confirm the transaction
            await self.solana_transaction_sender_client.aconfirm_transaction(
                sent_transaction_sig
            )
            solana_client_logger.info(
                f"Transaction {sent_transaction_sig} confirmed. Rent has been recovered."
            )
            return True
        except Exception as e:
            solana_client_logger.warning(f"An error occurred: {e}")
            return False

    def close_associated_token_accounts_and_recover_rent(
        self,
        account_owner: Keypair,
        accounts_to_close: list[Pubkey],
        destination_pubkey: Pubkey,
        ata_program_id: Pubkey | None = None,
        commitment: Commitment = solana_payments_settings.RPC_COMMITMENT,
    ) -> bool:
        return self.base_solana_client.run_sync_from_async(
            self.aclose_associated_token_accounts_and_recover_rent,
            account_owner,
            accounts_to_close,
            destination_pubkey,
            ata_program_id=ata_program_id,
            commitment=commitment,
        )
