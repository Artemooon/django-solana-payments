import pytest
from django.contrib.auth import get_user_model


@pytest.fixture
def test_settings():
    """
    Default test settings for SOLANA_PAYMENTS.
    Tests can override specific values as needed.
    """
    return {
        "SOLANA_RPC_URL": "https://api.devnet.solana.com",
        "SOLANA_RECEIVER_ADDRESS": "11111111111111111111111111111111",
        "SOLANA_SENDER_ADDRESS": "11111111111111111111111111111111",
        "SOLANA_SENDER_KEYPAIR": "[1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56,57,58,59,60,61,62,63,64]",
        "ONE_TIME_WALLETS_ENCRYPTION_ENABLED": False,
    }


@pytest.fixture(autouse=True)
def reset_service_singletons():
    """
    Automatically reset service singleton instances before each test.
    Settings are read dynamically and don't need resetting.
    """
    from django_solana_payments.services.one_time_wallet_service import reset_one_time_wallet_service

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
