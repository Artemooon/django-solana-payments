import logging
from decimal import Decimal

from django.db import transaction
from solders.solders import Pubkey, TransactionConfirmationStatus

from django_solana_payments.choices import OneTimeWalletStateTypes
from django_solana_payments.models import OneTimePaymentWallet
from django_solana_payments.services.one_time_wallet_service import (
    one_time_wallet_service,
)
from django_solana_payments.settings import solana_payments_settings
from django_solana_payments.solana.base_solana_client import base_solana_client
from django_solana_payments.solana.enums import TransactionTypeEnum
from django_solana_payments.solana.solana_token_client import SolanaTokenClient
from django_solana_payments.solana.solana_transaction_builder import (
    SolanaTransactionBuilder,
)
from django_solana_payments.solana.solana_transaction_sender_client import (
    SolanaTransactionSenderClient,
)

logger = logging.getLogger(__name__)


def send_transaction_and_update_one_time_wallet(
    one_time_wallet: OneTimePaymentWallet,
    recipient_address: str,
    amount: Decimal,
    transaction_type: TransactionTypeEnum,
    token_mint_address: str = None,
    should_close_spl_one_time_wallets_atas: bool = True,
) -> None:
    # Validate that token_mint_address is provided for SPL transactions
    if transaction_type == TransactionTypeEnum.SPL and not token_mint_address:
        raise ValueError("token_mint_address is required when transaction_type is SPL")

    decrypted_sender_keypair = one_time_wallet_service.load_keypair(
        one_time_wallet.keypair_json
    )

    solana_token_client = SolanaTokenClient(base_solana_client=base_solana_client)
    solana_transaction_builder = SolanaTransactionBuilder(
        base_solana_client=base_solana_client, solana_token_client=solana_token_client
    )
    solana_transaction_sender_client = SolanaTransactionSenderClient(
        base_solana_client=base_solana_client,
        solana_transaction_builder=solana_transaction_builder,
    )
    recipient_address_pubkey = Pubkey.from_string(recipient_address)
    try:
        data = solana_transaction_sender_client.send_transfer_transaction(
            recipient=recipient_address_pubkey,
            sender_keypair=decrypted_sender_keypair,
            amount=amount,
            transaction_type=transaction_type,
            token_mint_address=Pubkey.from_string(token_mint_address),
        )
    except Exception as e:
        OneTimePaymentWallet.objects.filter(id=one_time_wallet.id).update(
            state=OneTimeWalletStateTypes.FAILED_TO_SEND_FUNDS,
            receiver_address=recipient_address,
        )
        logger.error(f"An unexpected error occurred: {e}")
        return

    if data.confirmation_status in (
        TransactionConfirmationStatus.Confirmed,
        TransactionConfirmationStatus.Finalized,
    ):
        state = OneTimeWalletStateTypes.SENT_FUNDS
        if should_close_spl_one_time_wallets_atas:
            one_time_wallet_service.close_one_time_wallet_atas(
                one_time_wallet,
                Pubkey.from_string(solana_payments_settings.SOLANA_FEE_PAYER_ADDRESS),
            )
    else:
        state = OneTimeWalletStateTypes.FAILED_TO_SEND_FUNDS

    OneTimePaymentWallet.objects.filter(id=one_time_wallet.id).update(
        state=state, receiver_address=recipient_address
    )


def send_solana_transaction_to_main_wallet(
    recipient_address: str,
    one_time_wallet: OneTimePaymentWallet,
    amount: Decimal,
    transaction_type: TransactionTypeEnum,
    token_mint_address: str = None,
):
    with transaction.atomic():
        OneTimePaymentWallet.objects.filter(id=one_time_wallet.id).update(
            state=OneTimeWalletStateTypes.PROCESSING_FUNDS
        )

        send_transaction_and_update_one_time_wallet(
            one_time_wallet=one_time_wallet,
            recipient_address=recipient_address,
            amount=amount,
            transaction_type=TransactionTypeEnum(transaction_type),
            token_mint_address=token_mint_address,
        )
