from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

from solders.pubkey import Pubkey

from django_solana_payments.solana.solana_balance_client import SolanaBalanceClient


def test_get_balance_by_address_converts_lamports_to_sol():
    fake_base = MagicMock()
    fake_base.LAMPORTS_PER_SOL = 1_000_000_000
    fake_base.http_client.get_balance.return_value = SimpleNamespace(value=2500000000)

    client = SolanaBalanceClient(base_solana_client=fake_base)
    address = Pubkey.from_bytes(bytes([1] * 32))

    result = client.get_balance_by_address(address)

    assert result == Decimal("2.5")
    fake_base.http_client.get_balance.assert_called_once_with(address)


def test_get_spl_token_balance_by_address_returns_zero_when_no_token_accounts():
    fake_base = MagicMock()
    fake_base.http_client.get_token_accounts_by_owner.return_value = SimpleNamespace(
        value=[]
    )

    client = SolanaBalanceClient(base_solana_client=fake_base)
    owner = Pubkey.from_bytes(bytes([2] * 32))
    mint = Pubkey.from_bytes(bytes([3] * 32))

    result = client.get_spl_token_balance_by_address(owner, mint)

    assert result == Decimal("0")
    fake_base.http_client.get_token_account_balance.assert_not_called()


def test_get_spl_token_balance_by_address_uses_first_token_account_and_decimals():
    fake_base = MagicMock()
    token_account = Pubkey.from_bytes(bytes([4] * 32))
    fake_base.http_client.get_token_accounts_by_owner.return_value = SimpleNamespace(
        value=[SimpleNamespace(pubkey=token_account)]
    )
    fake_base.http_client.get_token_account_balance.return_value = SimpleNamespace(
        value=SimpleNamespace(amount="1234567", decimals=6)
    )

    client = SolanaBalanceClient(base_solana_client=fake_base)
    owner = Pubkey.from_bytes(bytes([5] * 32))
    mint = Pubkey.from_bytes(bytes([6] * 32))

    result = client.get_spl_token_balance_by_address(owner, mint)

    assert result == Decimal("1.234567")
    fake_base.http_client.get_token_accounts_by_owner.assert_called_once()
    fake_base.http_client.get_token_account_balance.assert_called_once_with(
        Pubkey(token_account.__bytes__())
    )
