from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from asgiref.sync import async_to_sync
from solana.rpc.commitment import Confirmed
from solders.signature import Signature
from solders.transaction_status import TransactionConfirmationStatus

from django_solana_payments.solana.base_solana_client import BaseSolanaClient


def test_http_client_uses_configured_async_client_options(settings, test_settings):
    settings.SOLANA_PAYMENTS = {
        **test_settings,
        "RPC_TIMEOUT": 12.5,
        "RPC_EXTRA_HEADERS": {"x-api-key": "secret"},
        "RPC_PROXY": "http://localhost:8899",
        "RPC_RATE_LIMIT": 25,
    }
    fake_client = SimpleNamespace(close=AsyncMock())

    async def use_client():
        client_instance = BaseSolanaClient()
        async with client_instance.http_client() as client:
            assert client is fake_client

    with patch(
        "django_solana_payments.solana.base_solana_client.AsyncClient",
        return_value=fake_client,
    ) as mock_async_client:
        async_to_sync(use_client)()

    mock_async_client.assert_called_once_with(
        endpoint=test_settings["RPC_URL"],
        commitment=Confirmed,
        timeout=12.5,
        extra_headers={"x-api-key": "secret"},
        proxy="http://localhost:8899",
        rate_limit=25,
    )
    fake_client.close.assert_awaited_once()


def test_http_client_uses_custom_client_factory():
    fake_client = SimpleNamespace(close=AsyncMock())

    def client_factory():
        return fake_client

    async def use_client():
        client_instance = BaseSolanaClient(
            rpc_url="https://rpc.example.com",
            client_factory=client_factory,
        )
        async with client_instance.http_client() as client:
            assert client is fake_client

    with patch(
        "django_solana_payments.solana.base_solana_client.AsyncClient"
    ) as mock_async_client:
        async_to_sync(use_client)()

    mock_async_client.assert_not_called()
    fake_client.close.assert_awaited_once()


def test_run_sync_from_async_executes_async_callable():
    client = BaseSolanaClient(rpc_url="https://rpc.example.com")

    async def add_numbers(left, right):
        return left + right

    result = client.run_sync_from_async(add_numbers, 2, 3)

    assert result == 5


def test_asend_transaction_uses_http_client_context():
    fake_client = SimpleNamespace(
        send_transaction=AsyncMock(return_value="send-response"),
        close=AsyncMock(),
    )
    transaction = MagicMock()
    client = BaseSolanaClient(
        rpc_url="https://rpc.example.com",
        client_factory=lambda: fake_client,
    )

    result = async_to_sync(client.asend_transaction)(transaction)

    assert result == "send-response"
    fake_client.send_transaction.assert_awaited_once_with(transaction)
    fake_client.close.assert_awaited_once()


def test_send_transaction_uses_sync_bridge():
    client = BaseSolanaClient(rpc_url="https://rpc.example.com")
    transaction = MagicMock()

    with patch.object(
        client,
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
    client = BaseSolanaClient(
        rpc_url="https://rpc.example.com",
        client_factory=lambda: fake_client,
    )

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
    client = BaseSolanaClient(
        rpc_url="https://rpc.example.com",
        client_factory=lambda: fake_client,
    )

    result = async_to_sync(client.aconfirm_transaction)(signature)

    assert result.tx_signature == signature
    assert result.confirmation_status is None
    fake_client.close.assert_awaited_once()


def test_asend_transaction_with_retry_returns_signature_value():
    signature = Signature.from_bytes(bytes([9] * 64))
    transaction = MagicMock()
    client = BaseSolanaClient(rpc_url="https://rpc.example.com")

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
    client = BaseSolanaClient(rpc_url="https://rpc.example.com")

    with patch.object(client, "send_transaction", side_effect=error):
        with pytest.raises(httpx.HTTPStatusError):
            client.send_transaction_with_retry(transaction)
