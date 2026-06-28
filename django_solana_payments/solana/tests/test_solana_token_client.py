from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from asgiref.sync import async_to_sync
from solders.hash import Hash
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.signature import Signature
from spl.token.constants import TOKEN_PROGRAM_ID

from django_solana_payments.solana.solana_token_client import SolanaTokenClient


def make_rpc_resp(value):
    return SimpleNamespace(value=value)


def make_latest_blockhash(blockhash: bytes | None = None):
    if blockhash is None:
        hb = Hash(bytes([0] * 32))
    elif isinstance(blockhash, bytes):
        hb = Hash(blockhash)
    else:
        hb = Hash(bytes(str(blockhash), "utf-8").ljust(32, b"\0")[:32])
    return make_rpc_resp(SimpleNamespace(blockhash=hb))


def make_account_info(owner_pubkey: Pubkey):
    return make_rpc_resp(SimpleNamespace(owner=owner_pubkey))


def make_send_tx_response(sig_bytes=None):
    if sig_bytes is None:
        sig_bytes = bytes([0] * 64)
    return SimpleNamespace(value=Signature.from_bytes(sig_bytes))


def test_create_associated_token_addresses_for_mints_calls_send_and_confirm():
    fake_base = MagicMock()

    real_fee_payer = Keypair()
    fake_base.BASE_SENDER_KEYPAIR = real_fee_payer

    client = SolanaTokenClient(base_solana_client=fake_base)
    client.solana_transaction_sender_client = MagicMock()
    client.solana_transaction_sender_client.send_transaction_with_retry.return_value = (
        Signature.from_bytes(bytes([1] * 64))
    )
    client.solana_transaction_sender_client.confirm_transaction.return_value = None

    recipient = Pubkey.from_bytes(bytes([3] * 32))
    mints = [Pubkey.from_bytes(bytes([2] * 32))]

    with (
        patch.object(
            client,
            "get_latest_blockhash",
            return_value=make_latest_blockhash("HB1"),
        ),
        patch.object(
            client,
            "get_account_info",
            return_value=make_account_info(owner_pubkey=TOKEN_PROGRAM_ID),
        ),
        patch(
            "django_solana_payments.solana.solana_token_client.MessageV0.try_compile",
            return_value="message_obj",
        ) as mock_try_compile,
        patch(
            "django_solana_payments.solana.solana_token_client.VersionedTransaction",
            return_value="versioned_tx",
        ) as mock_versioned_transaction,
    ):
        sig = client.create_associated_token_addresses_for_mints(
            recipient=recipient, mints=mints
        )

    mock_try_compile.assert_called_once()
    mock_versioned_transaction.assert_called_once_with(
        "message_obj",
        [fake_base.BASE_SENDER_KEYPAIR],
    )
    client.solana_transaction_sender_client.send_transaction_with_retry.assert_called_once_with(
        "versioned_tx"
    )
    assert client.solana_transaction_sender_client.confirm_transaction.called
    assert (
        sig
        == client.solana_transaction_sender_client.send_transaction_with_retry.return_value
    )


def test_close_associated_token_accounts_and_recover_rent_sends_transaction():
    fake_base = MagicMock()
    fake_base.run_sync_from_async.side_effect = (
        lambda async_callable, *args, **kwargs: async_to_sync(async_callable)(
            *args, **kwargs
        )
    )

    real_fee_payer = Keypair()
    fake_base.BASE_SENDER_KEYPAIR = real_fee_payer

    dummy_owner = Keypair()

    account_to_close = Pubkey.from_bytes(bytes([5] * 32))
    client = SolanaTokenClient(base_solana_client=fake_base)
    client.solana_transaction_sender_client = MagicMock()
    client.solana_transaction_sender_client.asend_transaction_with_retry = AsyncMock(
        return_value=Signature.from_bytes(bytes([2] * 64))
    )
    client.solana_transaction_sender_client.aconfirm_transaction = AsyncMock(
        return_value=None
    )

    with (
        patch.object(
            client,
            "aget_balance",
            AsyncMock(return_value=make_rpc_resp(1)),
        ),
        patch.object(
            client,
            "aget_latest_blockhash",
            AsyncMock(return_value=make_latest_blockhash("HB2")),
        ),
        patch(
            "django_solana_payments.solana.solana_token_client.MessageV0.try_compile",
            return_value="message_obj",
        ) as mock_try_compile,
        patch(
            "django_solana_payments.solana.solana_token_client.VersionedTransaction",
            return_value="versioned_tx",
        ) as mock_versioned_transaction,
    ):
        result = client.close_associated_token_accounts_and_recover_rent(
            account_owner=dummy_owner,
            accounts_to_close=[account_to_close],
            destination_pubkey=Pubkey.from_bytes(bytes([6] * 32)),
        )

    assert result is True
    mock_try_compile.assert_called_once()
    mock_versioned_transaction.assert_called_once_with(
        "message_obj",
        [dummy_owner, fake_base.BASE_SENDER_KEYPAIR],
    )
    client.solana_transaction_sender_client.asend_transaction_with_retry.assert_called_once_with(
        "versioned_tx"
    )
    client.solana_transaction_sender_client.aconfirm_transaction.assert_called()
