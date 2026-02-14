from datetime import timedelta
from unittest.mock import patch

import pytest
from django.utils import timezone

from django_solana_payments.choices import SolanaPaymentStatusTypes, TokenTypes
from django_solana_payments.helpers import (
    get_payment_crypto_token_model,
    get_solana_payment_model,
)
from django_solana_payments.models import (
    OneTimePaymentWallet,
    SolanaPayPaymentCryptoPrice,
)
from django_solana_payments.services.solana_payments_service import (
    SolanaPaymentsService,
)

SolanaPayment = get_solana_payment_model()
PaymentCryptoToken = get_payment_crypto_token_model()


@pytest.mark.django_db
def test_check_expired_solana_payments_updates_only_expired_initiated_records(user):
    expired_wallet = OneTimePaymentWallet.objects.create(keypair_json="[1,2,3]")
    active_wallet = OneTimePaymentWallet.objects.create(keypair_json="[4,5,6]")
    confirmed_wallet = OneTimePaymentWallet.objects.create(keypair_json="[7,8,9]")

    expired_payment = SolanaPayment.objects.create(
        user=user,
        payment_address="11111111111111111111111111111111",
        one_time_payment_wallet=expired_wallet,
        status=SolanaPaymentStatusTypes.INITIATED,
        expiration_date=timezone.now() - timedelta(minutes=5),
    )
    active_payment = SolanaPayment.objects.create(
        user=user,
        payment_address="22222222222222222222222222222222",
        one_time_payment_wallet=active_wallet,
        status=SolanaPaymentStatusTypes.INITIATED,
        expiration_date=timezone.now() + timedelta(minutes=30),
    )
    confirmed_payment = SolanaPayment.objects.create(
        user=user,
        payment_address="33333333333333333333333333333333",
        one_time_payment_wallet=confirmed_wallet,
        status=SolanaPaymentStatusTypes.CONFIRMED,
        expiration_date=timezone.now() - timedelta(minutes=5),
    )

    SolanaPaymentsService().check_expired_solana_payments()

    expired_payment.refresh_from_db()
    active_payment.refresh_from_db()
    confirmed_payment.refresh_from_db()
    assert expired_payment.status == SolanaPaymentStatusTypes.EXPIRED
    assert active_payment.status == SolanaPaymentStatusTypes.INITIATED
    assert confirmed_payment.status == SolanaPaymentStatusTypes.CONFIRMED


@pytest.mark.django_db
def test_create_payment_crypto_prices_raises_when_no_active_tokens():
    assert PaymentCryptoToken.objects.filter(is_active=True).count() == 0

    with pytest.raises(ValueError, match="No active payment tokens found"):
        SolanaPaymentsService().create_payment_crypto_prices_from_allowed_payment_crypto_tokens()


@pytest.mark.django_db
def test_create_payment_crypto_prices_creates_prices_for_all_active_tokens(
    payment_token, spl_token
):
    PaymentCryptoToken.objects.create(
        name="Inactive token",
        symbol="INACTIVE",
        mint_address="So11111111111111111111111111111111111111111",
        token_type=TokenTypes.SPL,
        is_active=False,
        payment_crypto_price="10.00",
    )

    created = (
        SolanaPaymentsService().create_payment_crypto_prices_from_allowed_payment_crypto_tokens()
    )

    assert len(created) == 2
    assert SolanaPayPaymentCryptoPrice.objects.count() == 2
    created_token_ids = {
        price.token_id for price in SolanaPayPaymentCryptoPrice.objects.all()
    }
    assert created_token_ids == {payment_token.id, spl_token.id}


@pytest.mark.django_db
@patch(
    "django_solana_payments.services.solana_payments_service.one_time_wallet_service.create_one_time_wallet"
)
def test_create_payment_assigns_all_active_token_prices(
    mock_create_one_time_wallet, user, payment_token, spl_token
):
    wallet = OneTimePaymentWallet.objects.create(keypair_json="[1,2,3]")
    mock_create_one_time_wallet.return_value = (
        None,
        "44444444444444444444444444444444",
        wallet,
    )

    payment = SolanaPaymentsService().create_payment(
        {
            "user": user,
            "label": "Test payment",
            "message": "hello",
            "meta_data": {"order_id": "123"},
        }
    )

    assert payment.status == SolanaPaymentStatusTypes.INITIATED
    assert payment.one_time_payment_wallet_id is not None
    assert payment.crypto_prices.count() == 2


@patch(
    "django_solana_payments.services.solana_payments_service.one_time_wallet_service.close_expired_one_time_wallets"
)
@patch.object(
    SolanaPaymentsService,
    "check_expired_solana_payments",
    side_effect=RuntimeError("boom"),
)
def test_mark_not_finished_continues_when_check_expired_fails(
    _mock_check_expired, mock_close_wallets
):
    SolanaPaymentsService().mark_not_finished_solana_payments_as_expired_and_close_wallets_accounts()

    mock_close_wallets.assert_called_once_with(None)


@patch(
    "django_solana_payments.services.solana_payments_service.one_time_wallet_service.close_expired_one_time_wallets"
)
@patch.object(SolanaPaymentsService, "check_expired_solana_payments")
def test_mark_not_finished_handles_wallet_close_failure(
    mock_check_expired, mock_close_wallets
):
    mock_close_wallets.side_effect = RuntimeError("close failure")

    SolanaPaymentsService().mark_not_finished_solana_payments_as_expired_and_close_wallets_accounts(
        sleep_interval_seconds=0.1
    )

    mock_check_expired.assert_called_once()
    mock_close_wallets.assert_called_once_with(0.1)


@patch("django_solana_payments.services.solana_payments_service.SolanaBalanceClient")
@patch(
    "django_solana_payments.services.solana_payments_service.send_transaction_and_update_one_time_wallet"
)
@pytest.mark.django_db
def test_send_solana_payments_returns_early_when_no_wallets_to_process(
    mock_send_transaction, mock_balance_client
):
    SolanaPaymentsService().send_solana_payments_from_one_time_wallets()

    mock_balance_client.assert_not_called()
    mock_send_transaction.assert_not_called()
