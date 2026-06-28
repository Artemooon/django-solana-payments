from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from asgiref.sync import async_to_sync
from solana.rpc.commitment import Confirmed

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
