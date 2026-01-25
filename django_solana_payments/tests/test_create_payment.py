import pytest

from django_solana_payments.helpers import get_solana_payment_model
from django_solana_payments.services.solana_payments_service import (
    SolanaPaymentsService,
)

SolanaPayment = get_solana_payment_model()


@pytest.mark.django_db
def test_create_payment_authenticated_user(user, payment_token):
    payment_data = {
        "user": user,
        "label": "Test payment",
        "message": "Hello",
        "meta_data": {"order_id": "123"},
    }

    payment = SolanaPaymentsService().create_payment(payment_data)

    assert isinstance(payment, SolanaPayment)
    assert payment.user == user
    assert payment.payment_address is not None


@pytest.mark.django_db
def test_create_payment_guest_user(payment_token):
    payment_data = {
        "user": None,
        "label": None,
        "message": None,
        "meta_data": {},
    }

    payment = SolanaPaymentsService().create_payment(payment_data)

    assert payment.user is None
