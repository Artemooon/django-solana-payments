from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from solders.keypair import Keypair
from solders.signature import Signature
from solders.solders import TransactionConfirmationStatus

from django_solana_payments.choices import OneTimeWalletStateTypes
from django_solana_payments.services.main_wallet_service import (
    send_solana_transaction_to_main_wallet,
    send_transaction_and_update_one_time_wallet,
)
from django_solana_payments.solana.dtos import ConfirmTransactionDTO
from django_solana_payments.solana.enums import TransactionTypeEnum


@pytest.mark.django_db
def test_send_transaction_and_update_wallet_requires_mint_for_spl(one_time_wallet):
    with pytest.raises(
        ValueError,
        match="token_mint_address is required when transaction_type is SPL",
    ):
        send_transaction_and_update_one_time_wallet(
            one_time_wallet=one_time_wallet,
            recipient_address="11111111111111111111111111111111",
            amount=Decimal("1"),
            transaction_type=TransactionTypeEnum.SPL,
            token_mint_address=None,
        )


@pytest.mark.django_db
@patch(
    "django_solana_payments.services.main_wallet_service.SolanaTransactionSenderClient"
)
@patch("django_solana_payments.services.main_wallet_service.SolanaTransactionBuilder")
@patch("django_solana_payments.services.main_wallet_service.SolanaTokenClient")
@patch(
    "django_solana_payments.services.main_wallet_service.one_time_wallet_service.load_keypair"
)
def test_send_transaction_and_update_wallet_marks_failed_on_sender_exception(
    mock_load_keypair,
    _mock_token_client,
    _mock_tx_builder,
    mock_tx_sender_class,
    one_time_wallet,
):
    mock_load_keypair.return_value = Keypair()
    mock_sender = MagicMock()
    mock_sender.send_transfer_transaction.side_effect = RuntimeError("send failed")
    mock_tx_sender_class.return_value = mock_sender

    send_transaction_and_update_one_time_wallet(
        one_time_wallet=one_time_wallet,
        recipient_address="11111111111111111111111111111111",
        amount=Decimal("1"),
        transaction_type=TransactionTypeEnum.SPL,
        token_mint_address="So11111111111111111111111111111111111111111",
    )

    one_time_wallet.refresh_from_db()
    assert one_time_wallet.state == OneTimeWalletStateTypes.FAILED_TO_SEND_FUNDS
    assert one_time_wallet.receiver_address == "11111111111111111111111111111111"


@pytest.mark.django_db
@patch(
    "django_solana_payments.services.main_wallet_service.one_time_wallet_service.close_one_time_wallet_atas"
)
@patch(
    "django_solana_payments.services.main_wallet_service.SolanaTransactionSenderClient"
)
@patch("django_solana_payments.services.main_wallet_service.SolanaTransactionBuilder")
@patch("django_solana_payments.services.main_wallet_service.SolanaTokenClient")
@patch(
    "django_solana_payments.services.main_wallet_service.one_time_wallet_service.load_keypair"
)
def test_send_transaction_and_update_wallet_marks_sent_on_confirmed(
    mock_load_keypair,
    _mock_token_client,
    _mock_tx_builder,
    mock_tx_sender_class,
    mock_close_atas,
    one_time_wallet,
    settings,
):
    settings.SOLANA_PAYMENTS = {"FEE_PAYER_ADDRESS": "11111111111111111111111111111111"}

    mock_load_keypair.return_value = Keypair()
    signature = Signature.from_bytes(bytes([1] * 64))
    mock_sender = MagicMock()
    mock_sender.send_transfer_transaction.return_value = ConfirmTransactionDTO(
        tx_signature=signature,
        confirmation_status=TransactionConfirmationStatus.Confirmed,
    )
    mock_tx_sender_class.return_value = mock_sender

    send_transaction_and_update_one_time_wallet(
        one_time_wallet=one_time_wallet,
        recipient_address="11111111111111111111111111111111",
        amount=Decimal("1"),
        transaction_type=TransactionTypeEnum.SPL,
        token_mint_address="So11111111111111111111111111111111111111111",
    )

    one_time_wallet.refresh_from_db()
    assert one_time_wallet.state == OneTimeWalletStateTypes.SENT_FUNDS
    assert one_time_wallet.receiver_address == "11111111111111111111111111111111"
    mock_close_atas.assert_called_once()


@pytest.mark.django_db
@patch(
    "django_solana_payments.services.main_wallet_service.one_time_wallet_service.close_one_time_wallet_atas"
)
@patch(
    "django_solana_payments.services.main_wallet_service.SolanaTransactionSenderClient"
)
@patch("django_solana_payments.services.main_wallet_service.SolanaTransactionBuilder")
@patch("django_solana_payments.services.main_wallet_service.SolanaTokenClient")
@patch(
    "django_solana_payments.services.main_wallet_service.one_time_wallet_service.load_keypair"
)
def test_send_transaction_and_update_wallet_does_not_close_atas_when_disabled(
    mock_load_keypair,
    _mock_token_client,
    _mock_tx_builder,
    mock_tx_sender_class,
    mock_close_atas,
    one_time_wallet,
):
    mock_load_keypair.return_value = Keypair()
    signature = Signature.from_bytes(bytes([2] * 64))
    mock_sender = MagicMock()
    mock_sender.send_transfer_transaction.return_value = ConfirmTransactionDTO(
        tx_signature=signature,
        confirmation_status=TransactionConfirmationStatus.Finalized,
    )
    mock_tx_sender_class.return_value = mock_sender

    send_transaction_and_update_one_time_wallet(
        one_time_wallet=one_time_wallet,
        recipient_address="11111111111111111111111111111111",
        amount=Decimal("1"),
        transaction_type=TransactionTypeEnum.SPL,
        token_mint_address="So11111111111111111111111111111111111111111",
        should_close_spl_one_time_wallets_atas=False,
    )

    one_time_wallet.refresh_from_db()
    assert one_time_wallet.state == OneTimeWalletStateTypes.SENT_FUNDS
    mock_close_atas.assert_not_called()


@pytest.mark.django_db
@patch(
    "django_solana_payments.services.main_wallet_service.one_time_wallet_service.close_one_time_wallet_atas"
)
@patch(
    "django_solana_payments.services.main_wallet_service.SolanaTransactionSenderClient"
)
@patch("django_solana_payments.services.main_wallet_service.SolanaTransactionBuilder")
@patch("django_solana_payments.services.main_wallet_service.SolanaTokenClient")
@patch(
    "django_solana_payments.services.main_wallet_service.one_time_wallet_service.load_keypair"
)
def test_send_transaction_and_update_wallet_marks_failed_on_unconfirmed(
    mock_load_keypair,
    _mock_token_client,
    _mock_tx_builder,
    mock_tx_sender_class,
    mock_close_atas,
    one_time_wallet,
):
    mock_load_keypair.return_value = Keypair()
    signature = Signature.from_bytes(bytes([3] * 64))
    mock_sender = MagicMock()
    mock_sender.send_transfer_transaction.return_value = ConfirmTransactionDTO(
        tx_signature=signature,
        confirmation_status=TransactionConfirmationStatus.Processed,
    )
    mock_tx_sender_class.return_value = mock_sender

    send_transaction_and_update_one_time_wallet(
        one_time_wallet=one_time_wallet,
        recipient_address="11111111111111111111111111111111",
        amount=Decimal("1"),
        transaction_type=TransactionTypeEnum.SPL,
        token_mint_address="So11111111111111111111111111111111111111111",
    )

    one_time_wallet.refresh_from_db()
    assert one_time_wallet.state == OneTimeWalletStateTypes.FAILED_TO_SEND_FUNDS
    mock_close_atas.assert_not_called()


@pytest.mark.django_db
@patch(
    "django_solana_payments.services.main_wallet_service.send_transaction_and_update_one_time_wallet"
)
def test_send_solana_transaction_to_main_wallet_sets_processing_and_delegates(
    mock_send_and_update,
    one_time_wallet,
):
    send_solana_transaction_to_main_wallet(
        recipient_address="11111111111111111111111111111111",
        one_time_wallet=one_time_wallet,
        amount=Decimal("2"),
        transaction_type="native",
        token_mint_address=None,
    )

    one_time_wallet.refresh_from_db()
    assert one_time_wallet.state == OneTimeWalletStateTypes.PROCESSING_FUNDS
    mock_send_and_update.assert_called_once_with(
        one_time_wallet=one_time_wallet,
        recipient_address="11111111111111111111111111111111",
        amount=Decimal("2"),
        transaction_type=TransactionTypeEnum.NATIVE,
        token_mint_address=None,
    )
