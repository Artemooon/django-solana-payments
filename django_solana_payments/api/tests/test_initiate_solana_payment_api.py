import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from django_solana_payments.choices import SolanaPaymentStatusTypes
from django_solana_payments.helpers import get_solana_payment_model

pytestmark = pytest.mark.django_db

SolanaPayment = get_solana_payment_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture(autouse=True)
def api_test_settings(settings):
    settings.ROOT_URLCONF = "django_solana_payments.urls"


def test_initiate_payment_guest_user_returns_payment_address(api_client, payment_token):
    response = api_client.post("/initiate/", data={}, format="json")

    assert response.status_code == 201
    assert "payment_address" in response.data
    assert response.data["payment_address"]

    payment = SolanaPayment.objects.get(
        payment_address=response.data["payment_address"]
    )
    assert payment.user is None
    assert payment.status == SolanaPaymentStatusTypes.INITIATED


def test_initiate_payment_authenticated_user_overrides_payload_user(
    api_client, user, payment_token
):
    User = get_user_model()
    another_user = User.objects.create_user(
        username="another-user",
        password="password",
    )

    api_client.force_authenticate(user=user)
    response = api_client.post(
        "/initiate/",
        data={
            "user": another_user.id,
            "label": "Premium",
            "message": "Payment test",
            "meta_data": {"order_id": "42"},
        },
        format="json",
    )

    assert response.status_code == 201

    payment = SolanaPayment.objects.get(
        payment_address=response.data["payment_address"]
    )
    assert payment.user == user
    assert payment.label == "Premium"
    assert payment.message == "Payment test"
    assert payment.meta_data == {"order_id": "42"}


def test_initiate_payment_invalid_user_id_returns_400(api_client, payment_token):
    response = api_client.post(
        "/initiate/",
        data={"user": 999999},
        format="json",
    )

    assert response.status_code == 400
    assert "user" in response.data
