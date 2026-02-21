from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.utils import timezone
from solders.keypair import Keypair
from solders.pubkey import Pubkey

from django_solana_payments.choices import (
    OneTimeWalletStateTypes,
    SolanaPaymentStatusTypes,
    TokenTypes,
)
from django_solana_payments.exceptions import PaymentConfigurationError, PaymentError
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

    with pytest.raises(
        PaymentConfigurationError, match="No active payment tokens found"
    ):
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


@pytest.mark.django_db
@patch(
    "django_solana_payments.services.solana_payments_service.VerifyTransactionService.verify_transaction_and_process_payment"
)
def test_recheck_initiated_payments_and_process_reconciles_payment(
    mock_verify, solana_payment, payment_crypto_price, payment_token, spl_token
):
    extra_price = SolanaPayPaymentCryptoPrice.objects.create(
        token=spl_token, amount_in_crypto=spl_token.payment_crypto_price
    )
    solana_payment.crypto_prices.add(payment_crypto_price, extra_price)

    mock_verify.side_effect = [
        SolanaPaymentStatusTypes.INITIATED,
        SolanaPaymentStatusTypes.CONFIRMED,
    ]

    summary = SolanaPaymentsService().recheck_initiated_payments_and_process(limit=10)

    assert summary["scanned"] == 1
    assert summary["reconciled"] == 1
    assert summary["pending"] == 0
    assert summary["failed"] == 0
    assert summary["skipped_no_tokens"] == 0
    assert mock_verify.call_count == 2


@pytest.mark.django_db
def test_recheck_initiated_payments_and_process_skips_when_no_prices(solana_payment):
    solana_payment.crypto_prices.clear()

    summary = SolanaPaymentsService().recheck_initiated_payments_and_process()

    assert summary["scanned"] == 1
    assert summary["reconciled"] == 0
    assert summary["pending"] == 0
    assert summary["failed"] == 0
    assert summary["skipped_no_tokens"] == 1


@pytest.mark.django_db
@patch(
    "django_solana_payments.services.solana_payments_service.VerifyTransactionService.verify_transaction_and_process_payment"
)
def test_recheck_initiated_payments_and_process_counts_pending_on_payment_error(
    mock_verify, solana_payment, payment_crypto_price, payment_token
):
    solana_payment.crypto_prices.add(payment_crypto_price)
    mock_verify.side_effect = PaymentError("temporary issue")

    summary = SolanaPaymentsService().recheck_initiated_payments_and_process(limit=10)

    assert summary["scanned"] == 1
    assert summary["reconciled"] == 0
    assert summary["pending"] == 1
    assert summary["failed"] == 0
    assert summary["skipped_no_tokens"] == 0


@pytest.mark.django_db
@patch(
    "django_solana_payments.services.solana_payments_service.VerifyTransactionService.verify_transaction_and_process_payment"
)
def test_recheck_initiated_payments_and_process_counts_failed_on_unexpected_exception(
    mock_verify, solana_payment, payment_crypto_price, payment_token
):
    solana_payment.crypto_prices.add(payment_crypto_price)
    mock_verify.side_effect = RuntimeError("boom")

    summary = SolanaPaymentsService().recheck_initiated_payments_and_process(limit=10)

    assert summary["scanned"] == 1
    assert summary["reconciled"] == 0
    assert summary["pending"] == 0
    assert summary["failed"] == 1
    assert summary["skipped_no_tokens"] == 0


@pytest.mark.django_db
@patch("django_solana_payments.services.solana_payments_service.time.sleep")
@patch(
    "django_solana_payments.services.solana_payments_service.VerifyTransactionService.verify_transaction_and_process_payment"
)
def test_recheck_initiated_payments_and_process_respects_sleep_interval(
    mock_verify, mock_sleep, solana_payment, payment_crypto_price
):
    solana_payment.crypto_prices.add(payment_crypto_price)
    mock_verify.return_value = SolanaPaymentStatusTypes.INITIATED

    summary = SolanaPaymentsService().recheck_initiated_payments_and_process(
        sleep_interval_seconds=0.25
    )

    assert summary["scanned"] == 1
    mock_sleep.assert_called_once_with(0.25)


@pytest.mark.django_db
@patch("django_solana_payments.services.solana_payments_service.time.sleep")
@patch(
    "django_solana_payments.services.solana_payments_service.send_transaction_and_update_one_time_wallet"
)
@patch(
    "django_solana_payments.services.solana_payments_service.one_time_wallet_service.load_keypair"
)
@patch("django_solana_payments.services.solana_payments_service.SolanaBalanceClient")
def test_send_solana_payments_from_one_time_wallets_sends_native_balance(
    mock_balance_client_cls,
    mock_load_keypair,
    mock_send_transaction,
    mock_sleep,
    solana_payment,
    payment_token,
):
    wallet = solana_payment.one_time_payment_wallet
    wallet.state = OneTimeWalletStateTypes.PROCESSING_PAYMENT
    wallet.save(update_fields=["state", "updated"])
    setattr(solana_payment, "paid_token", payment_token)
    solana_payment.save(update_fields=["paid_token", "updated"])

    fake_keypair = Keypair()
    mock_load_keypair.return_value = fake_keypair
    mock_balance_client = mock_balance_client_cls.return_value
    mock_balance_client.get_balance_by_address.return_value = Decimal("0.5")
    mock_balance_client.get_spl_token_balance_by_address.return_value = None

    SolanaPaymentsService().send_solana_payments_from_one_time_wallets(
        sleep_interval_seconds=0.1
    )

    mock_sleep.assert_called_once_with(0.1)
    mock_send_transaction.assert_called_once()
    call_kwargs = mock_send_transaction.call_args.kwargs
    assert call_kwargs["one_time_wallet"].id == wallet.id
    assert call_kwargs["amount"] == Decimal("0.5")
    assert call_kwargs["transaction_type"].value == "native"
    assert call_kwargs["token_mint_address"] is None


@pytest.mark.django_db
@patch(
    "django_solana_payments.services.solana_payments_service.send_transaction_and_update_one_time_wallet"
)
@patch(
    "django_solana_payments.services.solana_payments_service.one_time_wallet_service.load_keypair"
)
@patch("django_solana_payments.services.solana_payments_service.SolanaBalanceClient")
def test_send_solana_payments_from_one_time_wallets_sends_spl_balance(
    mock_balance_client_cls,
    mock_load_keypair,
    mock_send_transaction,
    solana_payment,
    spl_token,
):
    wallet = solana_payment.one_time_payment_wallet
    wallet.state = OneTimeWalletStateTypes.PROCESSING_FUNDS
    wallet.save(update_fields=["state", "updated"])
    solana_payment.paid_token = spl_token
    solana_payment.save(update_fields=["paid_token", "updated"])

    fake_keypair = Keypair()
    mock_load_keypair.return_value = fake_keypair
    mock_balance_client = mock_balance_client_cls.return_value
    mock_balance_client.get_balance_by_address.return_value = Decimal("0")
    mock_balance_client.get_spl_token_balance_by_address.return_value = Decimal("12.5")

    SolanaPaymentsService().send_solana_payments_from_one_time_wallets()

    mock_send_transaction.assert_called_once()
    call_kwargs = mock_send_transaction.call_args.kwargs
    assert call_kwargs["one_time_wallet"].id == wallet.id
    assert call_kwargs["amount"] == Decimal("12.5")
    assert call_kwargs["transaction_type"].value == "spl"
    assert call_kwargs["token_mint_address"] == spl_token.mint_address
    owner_arg, mint_arg = (
        mock_balance_client.get_spl_token_balance_by_address.call_args[0]
    )
    assert owner_arg == fake_keypair.pubkey()
    assert mint_arg == Pubkey.from_string(spl_token.mint_address)


@pytest.mark.django_db
@patch(
    "django_solana_payments.services.solana_payments_service.send_transaction_and_update_one_time_wallet"
)
@patch(
    "django_solana_payments.services.solana_payments_service.one_time_wallet_service.close_expired_one_time_wallets"
)
@patch(
    "django_solana_payments.services.solana_payments_service.one_time_wallet_service.load_keypair"
)
@patch("django_solana_payments.services.solana_payments_service.SolanaBalanceClient")
def test_send_solana_payments_from_one_time_wallets_marks_wallet_expired_when_no_balance(
    mock_balance_client_cls,
    mock_load_keypair,
    mock_close_expired_wallets,
    mock_send_transaction,
    solana_payment,
):
    wallet = solana_payment.one_time_payment_wallet
    wallet.state = OneTimeWalletStateTypes.FAILED_TO_SEND_FUNDS
    wallet.save(update_fields=["state", "updated"])
    solana_payment.paid_token = None
    solana_payment.save(update_fields=["paid_token", "updated"])

    mock_load_keypair.return_value = Keypair()
    mock_balance_client = mock_balance_client_cls.return_value
    mock_balance_client.get_balance_by_address.return_value = Decimal("0")

    SolanaPaymentsService().send_solana_payments_from_one_time_wallets()

    mock_send_transaction.assert_not_called()
    mock_close_expired_wallets.assert_called_once_with(sleep_interval_seconds=0.2)
    wallet.refresh_from_db()
    assert wallet.state == OneTimeWalletStateTypes.PAYMENT_EXPIRED_AND_WALLET_CLOSED
