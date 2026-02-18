from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from solders.solders import Keypair, Pubkey

from django_solana_payments.choices import OneTimeWalletStateTypes, TokenTypes
from django_solana_payments.helpers import (
    get_payment_crypto_token_model,
    get_solana_payment_model,
)
from django_solana_payments.models import (
    OneTimePaymentWallet,
    SolanaPayPaymentCryptoPrice,
)
from django_solana_payments.services.one_time_wallet_service import OneTimeWalletService

pytestmark = pytest.mark.django_db

PaymentCryptoToken = get_payment_crypto_token_model()
SolanaPayment = get_solana_payment_model()


def _create_active_spl_token(symbol: str, mint_address: str):
    return PaymentCryptoToken.objects.create(
        name=f"{symbol} token",
        symbol=symbol,
        mint_address=mint_address,
        token_type=TokenTypes.SPL,
        is_active=True,
        payment_crypto_price=Decimal("1.00"),
    )


def test_create_one_time_wallet_skips_atas_when_disabled(settings, test_settings):
    settings.SOLANA_PAYMENTS = test_settings
    service = OneTimeWalletService()

    with patch.object(
        service, "create_atas_for_one_time_wallet_from_active_tokens"
    ) as mock_create_atas:
        keypair, payment_address, wallet = service.create_one_time_wallet(
            should_create_atas=False
        )

    assert str(keypair.pubkey()) == payment_address
    assert wallet.id is not None
    mock_create_atas.assert_not_called()


def test_create_one_time_wallet_creates_atas_when_enabled(settings, test_settings):
    settings.SOLANA_PAYMENTS = test_settings
    service = OneTimeWalletService()

    with patch.object(
        service, "create_atas_for_one_time_wallet_from_active_tokens"
    ) as mock_create_atas:
        _keypair, _payment_address, wallet = service.create_one_time_wallet(
            should_create_atas=True
        )

    mock_create_atas.assert_called_once_with(wallet)


def test_create_atas_for_one_time_wallet_uses_only_active_spl_tokens_and_chunks(
    settings, test_settings
):
    settings.SOLANA_PAYMENTS = test_settings
    service = OneTimeWalletService()

    PaymentCryptoToken.objects.create(
        name="SOL",
        symbol="SOL",
        mint_address=None,
        token_type=TokenTypes.NATIVE,
        is_active=True,
        payment_crypto_price=Decimal("0.1"),
    )
    _create_active_spl_token("USDC", str(Keypair().pubkey()))
    _create_active_spl_token("PYUSD", str(Keypair().pubkey()))
    PaymentCryptoToken.objects.create(
        name="Inactive SPL",
        symbol="INACTIVE",
        mint_address=str(Keypair().pubkey()),
        token_type=TokenTypes.SPL,
        is_active=False,
        payment_crypto_price=Decimal("0.1"),
    )
    wallet = OneTimePaymentWallet.objects.create(keypair_json=Keypair().to_json())
    sender = Keypair()

    with (
        patch.object(service, "load_keypair", return_value=sender),
        patch(
            "django_solana_payments.services.one_time_wallet_service.SolanaTokenClient.create_associated_token_addresses_for_mints"
        ) as mock_create_atas,
    ):
        service.create_atas_for_one_time_wallet_from_active_tokens(
            wallet, max_atas_per_tx=1
        )

    assert mock_create_atas.call_count == 2
    for call in mock_create_atas.call_args_list:
        assert call.kwargs["recipient"] == sender.pubkey()
        assert len(call.kwargs["mints"]) == 1


def test_close_one_time_wallet_atas_returns_true_when_no_related_spl_tokens(
    settings, test_settings, solana_payment, payment_token
):
    settings.SOLANA_PAYMENTS = test_settings
    service = OneTimeWalletService()
    SolanaPayPaymentCryptoPrice.objects.create(
        token=payment_token, amount_in_crypto=Decimal("0.1")
    )
    receiver = Pubkey.from_string(test_settings["FEE_PAYER_ADDRESS"])

    with (
        patch.object(service, "load_keypair", return_value=Keypair()),
        patch.object(
            service.solana_token_client,
            "close_associated_token_accounts_and_recover_rent",
        ) as mock_close,
    ):
        result = service.close_one_time_wallet_atas(
            solana_payment.one_time_payment_wallet, receiver
        )

    assert result is True
    mock_close.assert_not_called()


def test_close_one_time_wallet_atas_closes_only_zero_balance_accounts(
    settings, test_settings, solana_payment
):
    settings.SOLANA_PAYMENTS = test_settings
    service = OneTimeWalletService()

    token_a = _create_active_spl_token("USDCA", str(Keypair().pubkey()))
    token_b = _create_active_spl_token("USDCB", str(Keypair().pubkey()))
    solana_payment.crypto_prices.add(
        SolanaPayPaymentCryptoPrice.objects.create(
            token=token_a, amount_in_crypto=Decimal("1")
        )
    )
    solana_payment.crypto_prices.add(
        SolanaPayPaymentCryptoPrice.objects.create(
            token=token_b, amount_in_crypto=Decimal("1")
        )
    )

    sender = Keypair()
    receiver = Pubkey.from_string(test_settings["FEE_PAYER_ADDRESS"])
    ata1 = Keypair().pubkey()
    ata2 = Keypair().pubkey()
    owner = Keypair().pubkey()

    with (
        patch.object(service, "load_keypair", return_value=sender),
        patch.object(
            service.solana_token_client,
            "get_associated_token_address",
            side_effect=[ata1, ata2],
        ),
        patch(
            "django_solana_payments.services.one_time_wallet_service.base_solana_client.http_client.get_account_info",
            side_effect=[
                SimpleNamespace(value=SimpleNamespace(owner=owner)),
                SimpleNamespace(value=SimpleNamespace(owner=owner)),
            ],
        ),
        patch(
            "django_solana_payments.services.one_time_wallet_service.base_solana_client.http_client.get_token_account_balance",
            side_effect=[
                SimpleNamespace(value=SimpleNamespace(amount="0")),
                SimpleNamespace(value=SimpleNamespace(amount="9")),
            ],
        ),
        patch.object(
            service.solana_token_client,
            "close_associated_token_accounts_and_recover_rent",
            return_value="tx-signature",
        ) as mock_close,
    ):
        result = service.close_one_time_wallet_atas(
            solana_payment.one_time_payment_wallet, receiver, max_atas_per_tx=1
        )

    assert result is True
    mock_close.assert_called_once_with(
        sender,
        accounts_to_close=[ata1],
        destination_pubkey=receiver,
        ata_program_id=owner,
    )


def test_close_one_time_wallet_atas_returns_true_when_no_ata_is_eligible(
    settings, test_settings, solana_payment
):
    settings.SOLANA_PAYMENTS = test_settings
    service = OneTimeWalletService()

    token = _create_active_spl_token("USDCX", str(Keypair().pubkey()))
    solana_payment.crypto_prices.add(
        SolanaPayPaymentCryptoPrice.objects.create(
            token=token, amount_in_crypto=Decimal("1")
        )
    )

    sender = Keypair()
    receiver = Pubkey.from_string(test_settings["FEE_PAYER_ADDRESS"])

    with (
        patch.object(service, "load_keypair", return_value=sender),
        patch.object(
            service.solana_token_client,
            "get_associated_token_address",
            return_value=Keypair().pubkey(),
        ),
        patch(
            "django_solana_payments.services.one_time_wallet_service.base_solana_client.http_client.get_account_info",
            return_value=SimpleNamespace(value=None),
        ),
        patch.object(
            service.solana_token_client,
            "close_associated_token_accounts_and_recover_rent",
        ) as mock_close,
    ):
        result = service.close_one_time_wallet_atas(
            solana_payment.one_time_payment_wallet, receiver
        )

    assert result is True
    mock_close.assert_not_called()


def test_close_expired_one_time_wallets_updates_only_successfully_closed_wallets(
    settings, test_settings
):
    settings.SOLANA_PAYMENTS = test_settings
    service = OneTimeWalletService()

    wallet_1 = OneTimePaymentWallet.objects.create(
        keypair_json=Keypair().to_json(),
        state=OneTimeWalletStateTypes.PAYMENT_EXPIRED,
    )
    wallet_2 = OneTimePaymentWallet.objects.create(
        keypair_json=Keypair().to_json(),
        state=OneTimeWalletStateTypes.PAYMENT_EXPIRED,
    )
    wallet_3 = OneTimePaymentWallet.objects.create(
        keypair_json=Keypair().to_json(),
        state=OneTimeWalletStateTypes.CREATED,
    )

    with patch.object(
        service, "close_one_time_wallet_atas", side_effect=[True, False]
    ) as mock_close:
        service.close_expired_one_time_wallets()

    wallet_1.refresh_from_db()
    wallet_2.refresh_from_db()
    wallet_3.refresh_from_db()

    assert wallet_1.state == OneTimeWalletStateTypes.PAYMENT_EXPIRED_AND_WALLET_CLOSED
    assert wallet_2.state == OneTimeWalletStateTypes.PAYMENT_EXPIRED
    assert wallet_3.state == OneTimeWalletStateTypes.CREATED
    assert mock_close.call_count == 2
