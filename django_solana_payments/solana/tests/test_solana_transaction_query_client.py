from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from solana.exceptions import SolanaRpcException
from solders.pubkey import Pubkey
from solders.signature import Signature

from django_solana_payments.solana.solana_transaction_query_client import (
    SolanaTransactionQueryClient,
)


def _build_transaction_details(*instruction_types: str) -> SimpleNamespace:
    instructions = [
        SimpleNamespace(parsed={"type": instruction_type})
        for instruction_type in instruction_types
    ]
    return SimpleNamespace(
        value=SimpleNamespace(
            transaction=SimpleNamespace(
                transaction=SimpleNamespace(
                    message=SimpleNamespace(instructions=instructions)
                ),
                meta=SimpleNamespace(inner_instructions=[]),
            )
        )
    )


def test_is_one_time_wallet_setup_transaction_returns_true_for_setup_only_transaction():
    client = SolanaTransactionQueryClient(base_solana_client=MagicMock())
    transaction_details = _build_transaction_details(
        "createAccount",
        "initializeImmutableOwner",
        "initializeAccount3",
    )

    result = client.is_one_time_wallet_setup_transaction(transaction_details)

    assert result is True


def test_is_one_time_wallet_setup_transaction_returns_false_for_setup_plus_transfer():
    client = SolanaTransactionQueryClient(base_solana_client=MagicMock())
    transaction_details = _build_transaction_details(
        "createAccount",
        "initializeAccount3",
        "transferChecked",
    )

    result = client.is_one_time_wallet_setup_transaction(transaction_details)

    assert result is False


def test_get_transactions_for_address_returns_transactions_for_valid_signatures():
    fake_base = MagicMock()
    address = Pubkey.from_bytes(bytes([1] * 32))
    signature_one = Signature.from_bytes(bytes([2] * 64))
    signature_two = Signature.from_bytes(bytes([3] * 64))
    transaction_one = MagicMock()
    transaction_two = MagicMock()

    client = SolanaTransactionQueryClient(base_solana_client=fake_base)

    with (
        patch.object(
            client,
            "get_signatures_for_address",
            return_value=SimpleNamespace(
                value=[
                    SimpleNamespace(signature=signature_one),
                    SimpleNamespace(signature=signature_two),
                ]
            ),
        ) as mock_get_signatures,
        patch.object(
            client,
            "get_transaction",
            side_effect=[transaction_one, transaction_two],
        ) as mock_get_transaction,
    ):
        result = client.get_transactions_for_address(address=address, limit=2)

    assert result == [transaction_one, transaction_two]
    mock_get_signatures.assert_called_once()
    mock_get_transaction.assert_any_call(
        signature_one,
        encoding="jsonParsed",
        commitment="confirmed",
        max_supported_transaction_version=0,
    )
    mock_get_transaction.assert_any_call(
        signature_two,
        encoding="jsonParsed",
        commitment="confirmed",
        max_supported_transaction_version=0,
    )


def test_get_transactions_for_address_skips_signatures_with_rpc_errors():
    fake_base = MagicMock()
    address = Pubkey.from_bytes(bytes([4] * 32))
    signature_one = Signature.from_bytes(bytes([5] * 64))
    signature_two = Signature.from_bytes(bytes([6] * 64))
    transaction_two = MagicMock()

    client = SolanaTransactionQueryClient(base_solana_client=fake_base)

    with (
        patch.object(
            client,
            "get_signatures_for_address",
            return_value=SimpleNamespace(
                value=[
                    SimpleNamespace(signature=signature_one),
                    SimpleNamespace(signature=signature_two),
                ]
            ),
        ),
        patch.object(
            client,
            "get_transaction",
            side_effect=[
                SolanaRpcException(
                    Exception("boom"),
                    lambda *_args, **_kwargs: None,
                    None,
                    SimpleNamespace(),
                ),
                transaction_two,
            ],
        ),
    ):
        result = client.get_transactions_for_address(address=address, limit=2)

    assert result == [transaction_two]
