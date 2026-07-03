import json
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from django.test import RequestFactory, override_settings

pytest.importorskip("payments")
from payments import PaymentStatus

from django_solana_payments.choices import SolanaPaymentStatusTypes, TokenTypes
from django_solana_payments.exceptions import (
    InvalidPaymentAmountError,
    PaymentNotConfirmedError,
)
from django_solana_payments.integrations.django_payments.provider import (
    SolanaPaymentsProvider,
)


class DummyPayment:
    def __init__(self, extra_data: str = "{}"):
        self.extra_data = extra_data
        self.status = PaymentStatus.WAITING
        self.message = ""
        self.variant = "solana"
        self.total = Decimal("10.00")
        self.currency = "USD"
        self.token = "checkout-token"
        self.captured_amount = None
        self.transaction_id = ""
        self.description = "Demo checkout"
        self.saved_update_fields = None
        self.attrs = SimpleNamespace()

    def get_failure_url(self) -> str:
        return "/failure/"

    def get_success_url(self) -> str:
        return "/success/"

    def get_process_url(self) -> str:
        return "/process/"

    def save(self, update_fields=None):
        self.saved_update_fields = update_fields


def _build_payment_state(
    *,
    payment_address: str = "GjwcWFQYzemBtpUoN5fMAP2FZviTtMRWCmrppGuTthJS",
    token_id=None,
    token_type=TokenTypes.NATIVE,
    mint_address=None,
    meta_data=None,
):
    return json.dumps(
        {
            "solana_payment": {
                "payment_address": payment_address,
                "token_id": token_id,
                "token_type": token_type,
                "mint_address": mint_address,
                "meta_data": meta_data or {},
            }
        }
    )


@pytest.mark.django_db
@patch(
    "django_solana_payments.integrations.django_payments.provider.verify_transaction_and_process_payment"
)
def test_process_data_success_confirms_payment(
    mock_verify_transaction,
    payment_token,
):
    mock_verify_transaction.return_value = SolanaPaymentStatusTypes.CONFIRMED
    payment = DummyPayment(
        extra_data=_build_payment_state(
            token_id=payment_token.id,
            token_type=TokenTypes.NATIVE,
        )
    )
    request = RequestFactory().get("/process/", {"token_type": TokenTypes.NATIVE})

    response = SolanaPaymentsProvider().process_data(payment, request)

    assert response.status_code == 302
    assert response["Location"] == "/success/"
    assert payment.status == PaymentStatus.CONFIRMED
    assert payment.message == SolanaPaymentStatusTypes.CONFIRMED
    assert payment.captured_amount == payment.total
    assert (
        mock_verify_transaction.call_args.kwargs["payment_crypto_token"]
        == payment_token
    )


@pytest.mark.django_db
@patch(
    "django_solana_payments.integrations.django_payments.provider.verify_transaction_and_process_payment"
)
def test_process_data_uses_request_mint_and_token_type(
    mock_verify_transaction,
    payment_token,
    spl_token,
):
    mock_verify_transaction.return_value = SolanaPaymentStatusTypes.CONFIRMED
    payment = DummyPayment(
        extra_data=_build_payment_state(
            token_id=payment_token.id,
            token_type=TokenTypes.NATIVE,
        )
    )
    request = RequestFactory().get(
        "/process/",
        {
            "token_type": TokenTypes.SPL,
            "mint_address": spl_token.mint_address,
        },
    )

    response = SolanaPaymentsProvider().process_data(payment, request)

    assert response.status_code == 302
    assert response["Location"] == "/success/"
    assert payment.status == PaymentStatus.CONFIRMED
    assert payment.captured_amount == payment.total
    assert mock_verify_transaction.call_args.kwargs["payment_crypto_token"] == spl_token


@pytest.mark.django_db
@patch(
    "django_solana_payments.integrations.django_payments.provider.verify_transaction_and_process_payment"
)
def test_process_data_not_confirmed_keeps_waiting(
    mock_verify_transaction,
    payment_token,
):
    mock_verify_transaction.side_effect = PaymentNotConfirmedError("Not confirmed yet")
    payment = DummyPayment(
        extra_data=_build_payment_state(
            token_id=payment_token.id,
            token_type=TokenTypes.NATIVE,
        )
    )
    request = RequestFactory().get("/process/", {"token_type": TokenTypes.NATIVE})

    response = SolanaPaymentsProvider().process_data(payment, request)

    assert response.status_code == 302
    assert response["Location"] == "/failure/"
    assert payment.status == PaymentStatus.WAITING
    assert payment.message == "Not confirmed yet"


@pytest.mark.django_db
@patch(
    "django_solana_payments.integrations.django_payments.provider.verify_transaction_and_process_payment"
)
def test_process_data_invalid_amount_marks_error(
    mock_verify_transaction,
    payment_token,
):
    mock_verify_transaction.side_effect = InvalidPaymentAmountError(
        expected="0.2",
        actual="0",
    )
    payment = DummyPayment(
        extra_data=_build_payment_state(
            token_id=payment_token.id,
            token_type=TokenTypes.NATIVE,
        )
    )
    request = RequestFactory().get("/process/", {"token_type": TokenTypes.NATIVE})

    response = SolanaPaymentsProvider().process_data(payment, request)

    assert response.status_code == 302
    assert response["Location"] == "/failure/"
    assert payment.status == PaymentStatus.ERROR
    assert "Invalid transfer amount" in payment.message


@pytest.mark.django_db
@override_settings(
    STATIC_URL="/static/",
    TEMPLATES=[
        {
            "BACKEND": "django.template.backends.django.DjangoTemplates",
            "APP_DIRS": True,
        }
    ],
)
@patch.object(SolanaPaymentsProvider, "_get_or_create_solana_payment")
def test_get_form_renders_widget_markup(
    mock_get_or_create_solana_payment,
    payment_token,
):
    payment = DummyPayment()
    solana_payment = SimpleNamespace(
        id=321,
        payment_address="GjwcWFQYzemBtpUoN5fMAP2FZviTtMRWCmrppGuTthJS",
        label="Premium Plan",
        message="Monthly subscription",
        meta_data={"order_id": "sub-1001"},
    )
    token_price = SimpleNamespace(
        token=payment_token,
        amount_in_crypto=Decimal("0.1"),
    )
    solana_payment.crypto_prices = MagicMock()
    solana_payment.crypto_prices.select_related.return_value.all.return_value = [
        token_price
    ]
    mock_get_or_create_solana_payment.return_value = solana_payment

    provider = SolanaPaymentsProvider(widget_theme={"accent": "#0f766e"})

    form = provider.get_form(payment)
    rendered = form.render()

    assert 'data-payment-token="checkout-token"' in rendered
    assert "data-solana-payment-widget" in rendered
    assert 'type="module"' in rendered
    assert "/static/solana_payments/solana-payment-widget/widget.js" in rendered
    assert "/static/solana_payments/solana-payment-widget/widget.css" in rendered
    assert '"verifyEndpoint": "/process/"' in rendered
    assert '"tokenType": "NATIVE"' in rendered


@pytest.mark.django_db
@patch.object(SolanaPaymentsProvider, "_get_or_create_solana_payment")
def test_get_form_orders_initial_tokens_with_selected_token_first(
    mock_get_or_create_solana_payment,
    payment_token,
):
    payment = DummyPayment()
    other_token = SimpleNamespace(
        id=999,
        token_type="SPL",
        mint_address="Mint111111111111111111111111111111111111111",
        name="USD Coin",
        symbol="USDC",
    )
    selected_token_price = SimpleNamespace(
        token=payment_token,
        amount_in_crypto=Decimal("0.1"),
    )
    other_token_price = SimpleNamespace(
        token=other_token,
        amount_in_crypto=Decimal("1.5"),
    )
    solana_payment = SimpleNamespace(
        id=321,
        payment_address="GjwcWFQYzemBtpUoN5fMAP2FZviTtMRWCmrppGuTthJS",
        label="Premium Plan",
        message="Monthly subscription",
        meta_data={"order_id": "sub-1001"},
    )
    solana_payment.crypto_prices = MagicMock()
    solana_payment.crypto_prices.select_related.return_value.all.return_value = [
        other_token_price,
        selected_token_price,
    ]
    mock_get_or_create_solana_payment.return_value = solana_payment

    provider = SolanaPaymentsProvider(
        token_selector=lambda payment, solana_payment, token_prices: selected_token_price,
    )

    form = provider.get_form(payment)

    initial_tokens = form.widget_config["tokens"]["initialTokens"]

    assert initial_tokens[0]["id"] == payment_token.id
    assert initial_tokens[0]["amount"] == "0.1"
    assert initial_tokens[1]["id"] == 999
