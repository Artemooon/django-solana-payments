from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from asgiref.sync import async_to_sync
from solana.rpc.commitment import Confirmed
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.signature import Signature
from solders.transaction_status import TransactionConfirmationStatus

from django_solana_payments.solana.base_solana_client import BaseSolanaClient
from django_solana_payments.solana.dtos import ConfirmTransactionDTO
from django_solana_payments.solana.enums import TransactionTypeEnum
from django_solana_payments.solana.solana_transaction_sender_client import (
    SolanaTransactionSenderClient,
)


def test_asend_transaction_uses_http_client_context():
    fake_client = SimpleNamespace(
        send_transaction=AsyncMock(return_value="send-response"),
        close=AsyncMock(),
    )
    transaction = MagicMock()
    base_client = BaseSolanaClient(
        rpc_url="https://rpc.example.com",
        client_factory=lambda: fake_client,
    )
    client = SolanaTransactionSenderClient(base_solana_client=base_client)

    result = async_to_sync(client.asend_transaction)(transaction)

    assert result == "send-response"
    fake_client.send_transaction.assert_awaited_once_with(transaction)
    fake_client.close.assert_awaited_once()


def test_send_transaction_uses_sync_bridge():
    base_client = BaseSolanaClient(rpc_url="https://rpc.example.com")
    client = SolanaTransactionSenderClient(base_solana_client=base_client)
    transaction = MagicMock()

    with patch.object(
        base_client,
        "run_sync_from_async",
        return_value="sync-response",
    ) as mock_run_sync:
        result = client.send_transaction(transaction)

    assert result == "sync-response"
    mock_run_sync.assert_called_once_with(client.asend_transaction, transaction)


def test_aconfirm_transaction_returns_confirmed_dto():
    signature = Signature.from_bytes(bytes([7] * 64))
    confirmation_entry = SimpleNamespace(
        confirmation_status=TransactionConfirmationStatus.Confirmed
    )
    fake_client = SimpleNamespace(
        confirm_transaction=AsyncMock(
            return_value=SimpleNamespace(value=[confirmation_entry])
        ),
        close=AsyncMock(),
    )
    base_client = BaseSolanaClient(
        rpc_url="https://rpc.example.com",
        client_factory=lambda: fake_client,
    )
    client = SolanaTransactionSenderClient(base_solana_client=base_client)

    result = async_to_sync(client.aconfirm_transaction)(signature)

    assert result.tx_signature == signature
    assert result.confirmation_status == TransactionConfirmationStatus.Confirmed
    fake_client.confirm_transaction.assert_awaited_once_with(
        signature,
        commitment=Confirmed,
    )
    fake_client.close.assert_awaited_once()


def test_aconfirm_transaction_returns_unconfirmed_dto_when_no_data():
    signature = Signature.from_bytes(bytes([8] * 64))
    fake_client = SimpleNamespace(
        confirm_transaction=AsyncMock(return_value=SimpleNamespace(value=[])),
        close=AsyncMock(),
    )
    base_client = BaseSolanaClient(
        rpc_url="https://rpc.example.com",
        client_factory=lambda: fake_client,
    )
    client = SolanaTransactionSenderClient(base_solana_client=base_client)

    result = async_to_sync(client.aconfirm_transaction)(signature)

    assert result.tx_signature == signature
    assert result.confirmation_status is None
    fake_client.close.assert_awaited_once()


def test_asend_transaction_with_retry_returns_signature_value():
    signature = Signature.from_bytes(bytes([9] * 64))
    transaction = MagicMock()
    client = SolanaTransactionSenderClient(
        base_solana_client=BaseSolanaClient(rpc_url="https://rpc.example.com")
    )

    with patch.object(
        client,
        "asend_transaction",
        AsyncMock(return_value=SimpleNamespace(value=signature)),
    ) as mock_send:
        result = async_to_sync(client.asend_transaction_with_retry)(transaction)

    assert result == signature
    mock_send.assert_awaited_once_with(transaction)


def test_send_transaction_with_retry_raises_http_status_error():
    request = httpx.Request("POST", "https://rpc.example.com")
    response = httpx.Response(status_code=500, request=request)
    error = httpx.HTTPStatusError("boom", request=request, response=response)
    transaction = MagicMock()
    client = SolanaTransactionSenderClient(
        base_solana_client=BaseSolanaClient(rpc_url="https://rpc.example.com")
    )

    with patch.object(client, "send_transaction", side_effect=error):
        with pytest.raises(httpx.HTTPStatusError):
            client.send_transaction_with_retry(transaction)


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
    client = SolanaTransactionSenderClient(
        base_solana_client=fake_base,
        solana_transaction_builder=fake_builder,
    )
    client.send_transaction_with_retry = MagicMock(return_value=signature)
    client.confirm_transaction = MagicMock(return_value=expected)

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
    client.send_transaction_with_retry.assert_called_once_with(transaction)
    client.confirm_transaction.assert_called_once_with(signature)
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
    client = SolanaTransactionSenderClient(
        base_solana_client=fake_base,
        solana_transaction_builder=fake_builder,
    )
    client.send_transaction_with_retry = MagicMock(return_value=signature)
    client.confirm_transaction = MagicMock(
        return_value=ConfirmTransactionDTO(tx_signature=signature)
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
