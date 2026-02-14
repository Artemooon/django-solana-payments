from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.signature import Signature

from django_solana_payments.solana.dtos import ConfirmTransactionDTO
from django_solana_payments.solana.enums import TransactionTypeEnum
from django_solana_payments.solana.solana_transaction_sender_client import (
    SolanaTransactionSenderClient,
)


def test_send_transfer_transaction_native_uses_builder_and_confirms():
    fake_base = MagicMock()
    fake_builder = MagicMock()
    sender_keypair = Keypair()
    recipient = Pubkey.from_bytes(bytes([9] * 32))
    transaction = object()
    signature = Signature.from_bytes(bytes([1] * 64))
    expected = ConfirmTransactionDTO(tx_signature=signature)

    fake_base.BASE_SENDER_KEYPAIR = sender_keypair
    fake_builder.create_native_transaction.return_value = transaction
    fake_base.send_transaction_with_retry.return_value = signature
    fake_base.confirm_transaction.return_value = expected

    client = SolanaTransactionSenderClient(
        base_solana_client=fake_base,
        solana_transaction_builder=fake_builder,
    )

    result = client.send_transfer_transaction(
        recipient=recipient,
        amount=Decimal("0.5"),
        transaction_type=TransactionTypeEnum.NATIVE,
    )

    fake_builder.create_native_transaction.assert_called_once_with(
        recipient=recipient,
        amount=Decimal("0.5"),
        sender_keypair=sender_keypair,
    )
    fake_base.send_transaction_with_retry.assert_called_once_with(transaction)
    fake_base.confirm_transaction.assert_called_once_with(signature)
    assert result == expected


def test_send_transfer_transaction_spl_requires_mint_address():
    fake_base = MagicMock()
    fake_builder = MagicMock()
    fake_base.BASE_SENDER_KEYPAIR = Keypair()
    recipient = Pubkey.from_bytes(bytes([7] * 32))

    client = SolanaTransactionSenderClient(
        base_solana_client=fake_base,
        solana_transaction_builder=fake_builder,
    )

    with pytest.raises(ValueError, match="token_mint_address is required"):
        client.send_transfer_transaction(
            recipient=recipient,
            amount=Decimal("1"),
            transaction_type=TransactionTypeEnum.SPL,
        )


def test_send_transfer_transaction_spl_uses_builder_and_confirm():
    fake_base = MagicMock()
    fake_builder = MagicMock()
    sender_keypair = Keypair()
    recipient = Pubkey.from_bytes(bytes([5] * 32))
    mint_address = Pubkey.from_bytes(bytes([6] * 32))
    transaction = object()
    signature = Signature.from_bytes(bytes([2] * 64))

    fake_base.BASE_SENDER_KEYPAIR = sender_keypair
    fake_builder.create_spl_token_transaction.return_value = transaction
    fake_base.send_transaction_with_retry.return_value = signature
    fake_base.confirm_transaction.return_value = ConfirmTransactionDTO(
        tx_signature=signature
    )

    client = SolanaTransactionSenderClient(
        base_solana_client=fake_base,
        solana_transaction_builder=fake_builder,
    )

    result = client.send_transfer_transaction(
        recipient=recipient,
        amount=Decimal("12.34"),
        transaction_type=TransactionTypeEnum.SPL,
        token_mint_address=mint_address,
    )

    fake_builder.create_spl_token_transaction.assert_called_once_with(
        recipient=recipient,
        amount=Decimal("12.34"),
        sender_keypair=sender_keypair,
        token_mint_address=mint_address,
    )
    assert result.tx_signature == signature


def test_send_transfer_transaction_returns_none_when_no_sender_keypair():
    fake_base = MagicMock()
    fake_builder = MagicMock()
    fake_base.BASE_SENDER_KEYPAIR = None
    recipient = Pubkey.from_bytes(bytes([8] * 32))

    client = SolanaTransactionSenderClient(
        base_solana_client=fake_base,
        solana_transaction_builder=fake_builder,
    )

    result = client.send_transfer_transaction(
        recipient=recipient,
        amount=Decimal("1"),
        transaction_type=TransactionTypeEnum.NATIVE,
    )

    assert result is None
    fake_builder.create_native_transaction.assert_not_called()
    fake_base.send_transaction_with_retry.assert_not_called()


def test_send_transfer_transaction_invalid_type_raises_assertion():
    fake_base = MagicMock()
    fake_builder = MagicMock()
    recipient = Pubkey.from_bytes(bytes([4] * 32))

    client = SolanaTransactionSenderClient(
        base_solana_client=fake_base,
        solana_transaction_builder=fake_builder,
    )

    with pytest.raises(AssertionError):
        client.send_transfer_transaction(
            recipient=recipient,
            amount=Decimal("1"),
            transaction_type="native",
        )
