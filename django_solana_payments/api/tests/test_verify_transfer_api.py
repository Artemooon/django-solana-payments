from datetime import timedelta
from unittest.mock import patch

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from django_solana_payments.choices import (
    OneTimeWalletStateTypes,
    SolanaPaymentStatusTypes,
)
from django_solana_payments.exceptions import (
    InvalidPaymentAmountError,
    PaymentNotConfirmedError,
)
from django_solana_payments.helpers import get_solana_payment_model
from django_solana_payments.models import OneTimePaymentWallet

pytestmark = pytest.mark.django_db

SolanaPayment = get_solana_payment_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture(autouse=True)
def api_test_settings(settings):
    settings.ROOT_URLCONF = "django_solana_payments.urls"


def test_verify_transfer_payment_address_not_found_returns_404(
    api_client, payment_token
):
    response = api_client.get(
        "/verify-transfer/11111111111111111111111111111111",
        {"token_type": "NATIVE"},
    )

    assert response.status_code == 404
    assert "detail" in response.data
    assert "was not found" in str(response.data["detail"])


def test_verify_transfer_invalid_token_type_returns_400(api_client):
    response = api_client.get(
        "/verify-transfer/11111111111111111111111111111111",
        {"token_type": "invalid-token-type"},
    )

    assert response.status_code == 400
    assert "token_type" in response.data


def test_verify_transfer_invalid_token_type_and_mint_address_returns_400(api_client):
    response = api_client.get(
        "/verify-transfer/11111111111111111111111111111111",
        {
            "token_type": "NATIVE",
            "mint_address": "Gh9ZwEmdLJ8DscKNTkTqPbNwLNNBjuSzaG9Vp2KGtKJr",
        },
    )

    assert response.status_code == 400
    assert "non_field_errors" in response.data
    assert "must be null for native SOL" in str(response.data["non_field_errors"][0])


@patch(
    "django_solana_payments.api.views.verify_transfer.VerifyTransactionService.verify_transaction_and_process_payment"
)
def test_verify_transfer_success_returns_status_and_payment_address(
    mock_verify_transaction,
    api_client,
    payment_token,
    solana_payment,
):
    mock_verify_transaction.return_value = SolanaPaymentStatusTypes.CONFIRMED

    response = api_client.get(
        f"/verify-transfer/{solana_payment.payment_address}",
        {"token_type": "NATIVE"},
    )

    assert response.status_code == 200
    assert response.data == {
        "status": SolanaPaymentStatusTypes.CONFIRMED,
        "payment_address": solana_payment.payment_address,
    }


def test_verify_transfer_payment_expired_returns_404_and_marks_payment_expired(
    api_client, payment_token, solana_payment
):
    SolanaPayment.objects.filter(id=solana_payment.id).update(
        status=SolanaPaymentStatusTypes.INITIATED,
        expiration_date=timezone.now() - timedelta(minutes=5),
    )

    response = api_client.get(
        f"/verify-transfer/{solana_payment.payment_address}",
        {"token_type": "NATIVE"},
    )

    assert response.status_code == 404
    assert "detail" in response.data
    assert "expired" in str(response.data["detail"]).lower()

    # The view is wrapped in transaction.atomic, so DB updates made before the
    # exception are rolled back.
    solana_payment.refresh_from_db()
    assert solana_payment.status == SolanaPaymentStatusTypes.INITIATED

    wallet = OneTimePaymentWallet.objects.get(
        id=solana_payment.one_time_payment_wallet_id
    )
    assert wallet.state == OneTimeWalletStateTypes.CREATED


@patch(
    "django_solana_payments.api.views.verify_transfer.VerifyTransactionService.verify_transaction_and_process_payment"
)
def test_verify_transfer_invalid_amount_returns_409(
    mock_verify_transaction, api_client, payment_token, solana_payment
):
    mock_verify_transaction.side_effect = InvalidPaymentAmountError(
        expected="1.0", actual="0.5"
    )

    response = api_client.get(
        f"/verify-transfer/{solana_payment.payment_address}",
        {"token_type": "NATIVE"},
    )

    assert response.status_code == 409
    assert "detail" in response.data
    assert "Invalid transfer amount" in str(response.data["detail"])


@patch(
    "django_solana_payments.api.views.verify_transfer.VerifyTransactionService.verify_transaction_and_process_payment"
)
def test_verify_transfer_invalid_balance_not_confirmed_returns_409(
    mock_verify_transaction, api_client, payment_token, solana_payment
):
    mock_verify_transaction.side_effect = PaymentNotConfirmedError("Not confirmed yet")

    response = api_client.get(
        f"/verify-transfer/{solana_payment.payment_address}",
        {"token_type": "NATIVE"},
    )

    assert response.status_code == 409
    assert "detail" in response.data


def test_verify_transfer_unsupported_mint_address_returns_400(api_client):
    response = api_client.get(
        "/verify-transfer/11111111111111111111111111111111",
        {
            "token_type": "SPL",
            "mint_address": "Gh9ZwEmdLJ8DscKNTkTqPbNwLNNBjuSzaG9Vp2KGtKJr",
        },
    )

    assert response.status_code == 400
    assert "detail" in response.data
    assert "Token is not supported" in str(response.data["detail"])
