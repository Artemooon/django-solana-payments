from datetime import timedelta
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from django_solana_payments.choices import (
    OneTimeWalletStateTypes,
    SolanaPaymentStatusTypes,
    TokenTypes,
)
from django_solana_payments.helpers import (
    get_payment_crypto_token_model,
    get_solana_payment_model,
)
from django_solana_payments.models import (
    OneTimePaymentWallet,
    SolanaPayPaymentCryptoPrice,
)
from django_solana_payments.services.one_time_wallet_service import (
    reset_one_time_wallet_service,
)

SolanaPayment = get_solana_payment_model()
PaymentCryptoToken = get_payment_crypto_token_model()


@pytest.fixture
def test_settings():
    """
    Default test settings for SOLANA_PAYMENTS.
    Tests can override specific values as needed.
    """
    return {
        "SOLANA_RPC_URL": "https://api.devnet.solana.com",
        "SOLANA_RECEIVER_ADDRESS": "11111111111111111111111111111111",
        "SOLANA_FEE_PAYER_ADDRESS": "11111111111111111111111111111111",
        "SOLANA_FEE_PAYER_KEYPAIR": "[1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56,57,58,59,60,61,62,63,64]",
        "ONE_TIME_WALLETS_ENCRYPTION_ENABLED": False,
    }


@pytest.fixture(autouse=True)
def reset_service_singletons():
    """
    Automatically reset service singleton instances before each test.
    Settings are read dynamically and don't need resetting.
    """
    # Reset before test
    reset_one_time_wallet_service()

    yield

    # Reset after test (cleanup)
    reset_one_time_wallet_service()


@pytest.fixture
def user(db):
    """
    Fixture to create a user for tests.
    """
    User = get_user_model()
    return User.objects.create_user(username="testuser", password="password")


@pytest.fixture
def payment_token(db):
    return PaymentCryptoToken.objects.create(
        name="Solana",
        symbol="SOL",
        mint_address=None,
        token_type=TokenTypes.NATIVE,
        is_active=True,
        payment_crypto_price=Decimal("0.1"),
    )


@pytest.fixture
def spl_token(db):
    return PaymentCryptoToken.objects.create(
        name="USD Coin",
        symbol="USDC",
        mint_address="Gh9ZwEmdLJ8DscKNTkTqPbNwLNNBjuSzaG9Vp2KGtKJr",
        token_type=TokenTypes.SPL,
        is_active=True,
        payment_crypto_price=Decimal("120.00"),
    )


@pytest.fixture
def one_time_wallet(db):
    """Create a one-time payment wallet."""
    return OneTimePaymentWallet.objects.create(
        keypair_json="[1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56,57,58,59,60,61,62,63,64]",
        state=OneTimeWalletStateTypes.CREATED,
    )


@pytest.fixture
def solana_payment(db, one_time_wallet, user):
    """Create a solana payment with valid Solana address."""
    payment = SolanaPayment.objects.create(
        user=user,
        payment_address="GjwcWFQYzemBtpUoN5fMAP2FZviTtMRWCmrppGuTthJS",
        one_time_payment_wallet=one_time_wallet,
        status=SolanaPaymentStatusTypes.INITIATED,
        expiration_date=timezone.now() + timedelta(hours=1),
        label="Test Payment",
        message="Test payment message",
    )
    return payment


@pytest.fixture
def payment_crypto_price(db, solana_payment, payment_token):
    """Create a payment crypto price."""
    price = SolanaPayPaymentCryptoPrice.objects.create(
        token=payment_token, amount_in_crypto=Decimal("0.1")
    )
    solana_payment.crypto_prices.add(price)
    return price
