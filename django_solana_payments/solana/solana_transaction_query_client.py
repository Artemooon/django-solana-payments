import json
import logging
from typing import Optional

from solana.exceptions import SolanaRpcException
from solana.rpc.commitment import Commitment
from solders.pubkey import Pubkey
from solders.signature import Signature
from solders.solders import EncodedTransactionWithStatusMeta, GetTransactionResp
from solders.transaction_status import TransactionStatus

from django_solana_payments.settings import solana_payments_settings
from django_solana_payments.solana.base_solana_client import BaseSolanaClient

logger = logging.getLogger(__name__)


class SolanaTransactionQueryClient:
    WALLET_SETUP_INSTRUCTION_TYPES = {
        "createAccount",
        "initializeImmutableOwner",
        "initializeAccount3",
    }

    def __init__(self, base_solana_client: BaseSolanaClient):
        self.base_solana_client = base_solana_client

    async def aget_signature_statuses(self, signatures: list[Signature]):
        async with self.base_solana_client.http_client() as client:
            return await client.get_signature_statuses(
                signatures,
                search_transaction_history=True,
            )

    def get_signature_statuses(self, signatures: list[Signature]):
        return self.base_solana_client.run_sync_from_async(
            self.aget_signature_statuses,
            signatures,
        )

    async def aget_signatures_for_address(
        self,
        address,
        limit: int | None = None,
        commitment: Commitment | None = None,
    ):
        if commitment is None:
            commitment = solana_payments_settings.RPC_COMMITMENT
        async with self.base_solana_client.http_client() as client:
            return await client.get_signatures_for_address(
                address,
                limit=limit,
                commitment=commitment,
            )

    def get_signatures_for_address(
        self,
        address,
        limit: int | None = None,
        commitment: Commitment | None = None,
    ):
        return self.base_solana_client.run_sync_from_async(
            self.aget_signatures_for_address,
            address,
            limit=limit,
            commitment=commitment,
        )

    async def aget_transaction(
        self,
        signature: Signature,
        encoding: str = "jsonParsed",
        commitment: Commitment | None = None,
        max_supported_transaction_version: int = 0,
    ):
        if commitment is None:
            commitment = solana_payments_settings.RPC_COMMITMENT
        async with self.base_solana_client.http_client() as client:
            return await client.get_transaction(
                signature,
                encoding=encoding,
                commitment=commitment,
                max_supported_transaction_version=max_supported_transaction_version,
            )

    def get_transaction(
        self,
        signature: Signature,
        encoding: str = "jsonParsed",
        commitment: Commitment | None = None,
        max_supported_transaction_version: int = 0,
    ):
        return self.base_solana_client.run_sync_from_async(
            self.aget_transaction,
            signature,
            encoding=encoding,
            commitment=commitment,
            max_supported_transaction_version=max_supported_transaction_version,
        )

    def get_signatures_statuses(
        self,
        signatures: list[Signature],
    ) -> list[Optional[TransactionStatus]]:
        response = self.get_signature_statuses(signatures)
        return response.value

    def get_transactions_for_address(
        self,
        address: Pubkey,
        limit: Optional[int] = 2,
        commitment: Commitment = solana_payments_settings.RPC_COMMITMENT,
    ) -> list[GetTransactionResp]:
        tx_signatures = self.get_signatures_for_address(
            address, limit=limit, commitment=commitment
        ).value
        transactions: list[GetTransactionResp] = []
        for tx in tx_signatures:
            try:
                transaction = self.get_transaction(
                    tx.signature,
                    encoding="jsonParsed",
                    commitment=commitment,
                    max_supported_transaction_version=0,
                )
            except SolanaRpcException as exc:
                logger.warning(
                    "Skipping transaction lookup for address=%s signature=%s due to RPC error: %s",
                    address,
                    tx.signature,
                    exc,
                )
                continue
            transactions.append(transaction)
        return transactions

    def extract_fee_payer_from_transaction_details(
        self, transaction_details
    ) -> Pubkey | None:
        tx_result = transaction_details.value.transaction.transaction

        if tx_result:
            fee_payer = tx_result.message.account_keys[0]

            return fee_payer

        return None

    def extract_instruction_types_from_transaction_details(
        self, transaction_details: GetTransactionResp
    ) -> set[str]:
        instruction_types: set[str] = set()
        transaction_wrapper: EncodedTransactionWithStatusMeta | None = getattr(
            transaction_details.value, "transaction"
        )
        if not transaction_wrapper:
            return instruction_types

        transaction = transaction_wrapper.transaction
        meta = transaction_wrapper.meta
        message = getattr(transaction, "message", None)

        for instruction in getattr(message, "instructions", []) or []:
            instruction_type = self._extract_instruction_type(instruction)
            if instruction_type:
                instruction_types.add(instruction_type)

        for inner_group in getattr(meta, "inner_instructions", []) or []:
            for instruction in getattr(inner_group, "instructions", []) or []:
                instruction_type = self._extract_instruction_type(instruction)
                if instruction_type:
                    instruction_types.add(instruction_type)

        return instruction_types

    def is_one_time_wallet_setup_transaction(
        self, transaction_details: GetTransactionResp
    ) -> bool:
        instruction_types = self.extract_instruction_types_from_transaction_details(
            transaction_details
        )
        if not instruction_types:
            return False

        return instruction_types.issubset(self.WALLET_SETUP_INSTRUCTION_TYPES)

    def _extract_instruction_type(self, instruction) -> str | None:
        parsed_payload = getattr(instruction, "parsed", None)
        if isinstance(parsed_payload, dict):
            instruction_type = parsed_payload.get("type")
            return instruction_type if isinstance(instruction_type, str) else None

        to_json = getattr(instruction, "to_json", None)
        if callable(to_json):
            try:
                payload = json.loads(to_json())
            except (TypeError, ValueError):
                return None

            if isinstance(payload, dict):
                parsed = payload.get("parsed")
                if isinstance(parsed, dict):
                    instruction_type = parsed.get("type")
                    if isinstance(instruction_type, str):
                        return instruction_type

        if isinstance(instruction, dict):
            parsed = instruction.get("parsed")
            if isinstance(parsed, dict):
                instruction_type = parsed.get("type")
                return instruction_type if isinstance(instruction_type, str) else None

        return None
