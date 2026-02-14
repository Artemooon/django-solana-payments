from types import SimpleNamespace
from unittest.mock import MagicMock

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

    fake_base.http_client.get_latest_blockhash.return_value = make_latest_blockhash(
        "HB1"
    )
    fake_base.http_client.get_account_info.return_value = make_account_info(
        owner_pubkey=TOKEN_PROGRAM_ID
    )

    fake_base.send_transaction_with_retry.return_value = Signature.from_bytes(
        bytes([1] * 64)
    )
    fake_base.confirm_transaction.return_value = None

    client = SolanaTokenClient(base_solana_client=fake_base)

    recipient = Pubkey.from_bytes(bytes([3] * 32))
    mints = [Pubkey.from_bytes(bytes([2] * 32))]

    sig = client.create_associated_token_addresses_for_mints(
        recipient=recipient, mints=mints
    )

    assert fake_base.send_transaction_with_retry.called
    assert fake_base.confirm_transaction.called
    assert sig == fake_base.send_transaction_with_retry.return_value


def test_close_associated_token_accounts_and_recover_rent_sends_transaction():
    fake_base = MagicMock()

    real_fee_payer = Keypair()
    fake_base.BASE_SENDER_KEYPAIR = real_fee_payer

    dummy_owner = Keypair()

    account_to_close = Pubkey.from_bytes(bytes([5] * 32))
    fake_base.http_client.get_balance.return_value = make_rpc_resp(1)

    fake_base.http_client.get_latest_blockhash.return_value = make_latest_blockhash(
        "HB2"
    )

    fake_base.send_transaction_with_retry.return_value = Signature.from_bytes(
        bytes([2] * 64)
    )
    fake_base.confirm_transaction.return_value = None

    client = SolanaTokenClient(base_solana_client=fake_base)

    result = client.close_associated_token_accounts_and_recover_rent(
        account_owner=dummy_owner,
        accounts_to_close=[account_to_close],
        destination_pubkey=Pubkey.from_bytes(bytes([6] * 32)),
    )

    assert result is True
    fake_base.send_transaction_with_retry.assert_called()
    fake_base.confirm_transaction.assert_called()
