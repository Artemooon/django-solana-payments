from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, call, patch

import pytest
from solders.hash import Hash
from solders.keypair import Keypair
from solders.pubkey import Pubkey

from django_solana_payments.solana.solana_transaction_builder import (
    SolanaTransactionBuilder,
)


def _latest_blockhash_response() -> SimpleNamespace:
    return SimpleNamespace(value=SimpleNamespace(blockhash=Hash(bytes([8] * 32))))


def test_calculate_spl_transaction_amount():
    builder = SolanaTransactionBuilder(
        base_solana_client=MagicMock(),
        solana_token_client=MagicMock(),
    )

    assert builder._calculate_spl_transaction_amount(Decimal("1.234567"), 6) == 1234567


def test_create_native_transaction_builds_message_and_transaction():
    fake_base = MagicMock()
    fake_base.LAMPORTS_PER_SOL = 1_000_000_000
    fake_base.BASE_SENDER_KEYPAIR = Keypair()
    fake_base.http_client.get_latest_blockhash.return_value = (
        _latest_blockhash_response()
    )
    fake_token_client = MagicMock()

    sender_keypair = Keypair()
    recipient = Pubkey.from_bytes(bytes([4] * 32))

    builder = SolanaTransactionBuilder(
        base_solana_client=fake_base,
        solana_token_client=fake_token_client,
    )

    with (
        patch(
            "django_solana_payments.solana.solana_transaction_builder.TransferParams"
        ) as mock_transfer_params,
        patch(
            "django_solana_payments.solana.solana_transaction_builder.transfer"
        ) as mock_transfer,
        patch(
            "django_solana_payments.solana.solana_transaction_builder.Message"
        ) as mock_message,
        patch(
            "django_solana_payments.solana.solana_transaction_builder.Transaction"
        ) as mock_transaction,
    ):
        mock_transfer_params.return_value = "transfer_params"
        mock_transfer.return_value = "transfer_ix"
        mock_message.return_value = "message_obj"
        mock_transaction.return_value = "tx_obj"

        result = builder.create_native_transaction(
            recipient=recipient,
            amount=Decimal("0.25"),
            sender_keypair=sender_keypair,
        )

    mock_transfer_params.assert_called_once_with(
        from_pubkey=sender_keypair.pubkey(),
        to_pubkey=recipient,
        lamports=250000000,
    )
    mock_transfer.assert_called_once_with("transfer_params")
    mock_message.assert_called_once_with(
        payer=fake_base.BASE_SENDER_KEYPAIR.pubkey(),
        instructions=["transfer_ix"],
    )
    mock_transaction.assert_called_once_with(
        message="message_obj",
        from_keypairs=[sender_keypair, fake_base.BASE_SENDER_KEYPAIR],
        recent_blockhash=fake_base.http_client.get_latest_blockhash.return_value.value.blockhash,
    )
    assert result == "tx_obj"


def test_create_spl_token_transaction_builds_instruction_and_transaction():
    fake_base = MagicMock()
    fake_base.BASE_SENDER_KEYPAIR = Keypair()
    fake_base.http_client.get_latest_blockhash.return_value = (
        _latest_blockhash_response()
    )

    token_program_id = Pubkey.from_bytes(bytes([1] * 32))
    fake_base.http_client.get_account_info.return_value = SimpleNamespace(
        value=SimpleNamespace(owner=token_program_id)
    )
    fake_base.http_client.get_token_supply.return_value = SimpleNamespace(
        value=SimpleNamespace(decimals=6)
    )

    fake_token_client = MagicMock()

    sender_keypair = Keypair()
    recipient = Pubkey.from_bytes(bytes([2] * 32))
    token_mint = Pubkey.from_bytes(bytes([3] * 32))
    sender_ata = Pubkey.from_bytes(bytes([5] * 32))
    recipient_ata = Pubkey.from_bytes(bytes([6] * 32))
    fake_token_client.get_or_create_associated_token_address.side_effect = [
        sender_ata,
        recipient_ata,
    ]

    builder = SolanaTransactionBuilder(
        base_solana_client=fake_base,
        solana_token_client=fake_token_client,
    )

    with (
        patch(
            "django_solana_payments.solana.solana_transaction_builder.SplTransferParams"
        ) as mock_spl_params,
        patch(
            "django_solana_payments.solana.solana_transaction_builder.spl_transfer"
        ) as mock_spl_transfer,
        patch(
            "django_solana_payments.solana.solana_transaction_builder.Message"
        ) as mock_message,
        patch(
            "django_solana_payments.solana.solana_transaction_builder.Transaction"
        ) as mock_transaction,
    ):
        mock_spl_params.return_value = "spl_params"
        mock_spl_transfer.return_value = "spl_ix"
        mock_message.return_value = "message_obj"
        mock_transaction.return_value = "tx_obj"

        result = builder.create_spl_token_transaction(
            recipient=recipient,
            amount=Decimal("1.23"),
            sender_keypair=sender_keypair,
            token_mint_address=token_mint,
        )

    fake_token_client.get_or_create_associated_token_address.assert_has_calls(
        [
            call(sender_keypair.pubkey(), token_mint),
            call(recipient, token_mint),
        ]
    )
    mock_spl_params.assert_called_once_with(
        program_id=token_program_id,
        source=sender_ata,
        dest=recipient_ata,
        owner=sender_keypair.pubkey(),
        amount=1230000,
    )
    mock_spl_transfer.assert_called_once_with("spl_params")
    mock_message.assert_called_once_with(
        payer=fake_base.BASE_SENDER_KEYPAIR.pubkey(),
        instructions=["spl_ix"],
    )
    mock_transaction.assert_called_once_with(
        message="message_obj",
        from_keypairs=[sender_keypair, fake_base.BASE_SENDER_KEYPAIR],
        recent_blockhash=fake_base.http_client.get_latest_blockhash.return_value.value.blockhash,
    )
    assert result == "tx_obj"


def test_create_spl_token_transaction_raises_when_mint_not_found():
    fake_base = MagicMock()
    fake_base.BASE_SENDER_KEYPAIR = Keypair()
    fake_base.http_client.get_account_info.return_value = SimpleNamespace(value=None)

    fake_token_client = MagicMock()
    fake_token_client.get_or_create_associated_token_address.side_effect = [
        Pubkey.from_bytes(bytes([5] * 32)),
        Pubkey.from_bytes(bytes([6] * 32)),
    ]

    builder = SolanaTransactionBuilder(
        base_solana_client=fake_base,
        solana_token_client=fake_token_client,
    )

    sender_keypair = Keypair()
    recipient = Pubkey.from_bytes(bytes([2] * 32))
    token_mint = Pubkey.from_bytes(bytes([3] * 32))

    with pytest.raises(ValueError, match="Mint account .* not found or invalid"):
        builder.create_spl_token_transaction(
            recipient=recipient,
            amount=Decimal("1"),
            sender_keypair=sender_keypair,
            token_mint_address=token_mint,
        )

    fake_base.http_client.get_token_supply.assert_not_called()
