from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from django_solana_payments.choices import TokenTypes
from django_solana_payments.helpers import get_payment_crypto_token_model

PaymentCryptoToken = get_payment_crypto_token_model()


@pytest.mark.django_db
def test_spl_token_invalid_mint_address_raises_validation_error():
    token = PaymentCryptoToken(
        name="Invalid SPL",
        symbol="ISPL",
        token_type=TokenTypes.SPL,
        mint_address="not-a-valid-solana-address",
        is_active=True,
        payment_crypto_price=Decimal("1.0"),
    )

    with pytest.raises(
        ValidationError, match="mint_address must be a valid Solana address"
    ):
        token.full_clean()


@pytest.mark.django_db
def test_spl_token_valid_mint_address_passes_validation():
    token = PaymentCryptoToken(
        name="Valid SPL",
        symbol="VSPL",
        token_type=TokenTypes.SPL,
        mint_address="So11111111111111111111111111111111111111111",
        is_active=True,
        payment_crypto_price=Decimal("1.0"),
    )

    token.full_clean()


@pytest.mark.django_db
def test_spl_token_invalid_mint_address_raises_on_create():
    with pytest.raises(
        ValidationError, match="mint_address must be a valid Solana address"
    ):
        PaymentCryptoToken.objects.create(
            name="Invalid SPL via create",
            symbol="ISPLC",
            token_type=TokenTypes.SPL,
            mint_address="invalid",
            is_active=True,
            payment_crypto_price=Decimal("1.0"),
        )
