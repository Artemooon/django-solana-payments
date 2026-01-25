import json

import pytest
from django.core.exceptions import ImproperlyConfigured
from solders.keypair import Keypair
from solders.pubkey import Pubkey

from django_solana_payments.services.one_time_wallet_service import OneTimeWalletService


@pytest.mark.django_db
def test_wallet_encryption_disabled(settings, test_settings):
    test_settings["ONE_TIME_WALLETS_ENCRYPTION_ENABLED"] = False
    settings.SOLANA_PAYMENTS = test_settings

    service = OneTimeWalletService()
    wallet = service.create_one_time_wallet()[2]

    # Should be stored as plain JSON array (not encrypted)
    assert wallet.keypair_json.startswith("[")

    # Should be able to parse as JSON and load as keypair
    json.loads(wallet.keypair_json)  # Verify it's valid JSON
    keypair = Keypair.from_json(wallet.keypair_json)  # Verify it's a valid keypair
    assert keypair is not None


def test_encryption_enabled_without_key(settings, test_settings):
    test_settings["ONE_TIME_WALLETS_ENCRYPTION_ENABLED"] = True
    # Don't set encryption key
    settings.SOLANA_PAYMENTS = test_settings

    with pytest.raises(ImproperlyConfigured):
        OneTimeWalletService()


@pytest.mark.django_db
def test_wallet_encryption_enabled(settings, test_settings):
    # Generate a valid Fernet key (base64-encoded 32 bytes)
    from cryptography.fernet import Fernet

    valid_key = Fernet.generate_key().decode("utf-8")

    test_settings["ONE_TIME_WALLETS_ENCRYPTION_ENABLED"] = True
    test_settings["ONE_TIME_WALLETS_ENCRYPTION_KEY"] = valid_key
    settings.SOLANA_PAYMENTS = test_settings

    service = OneTimeWalletService()
    wallet = service.create_one_time_wallet()[2]

    # Should NOT be plain JSON (should be encrypted)
    assert not wallet.keypair_json.startswith("[")

    # Should not be parseable as JSON
    with pytest.raises(json.JSONDecodeError):
        json.loads(wallet.keypair_json)

    # Should not be directly loadable as a keypair (it's encrypted)
    with pytest.raises(Exception):
        Keypair.from_json(wallet.keypair_json)

    # But should be decryptable via the wallet's address property
    address = wallet.address
    assert address is not None
    assert isinstance(address, Pubkey)
