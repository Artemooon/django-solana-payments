from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

SECRET_KEY = "test-secret-key"
DEBUG = True

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django_solana_payments",
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

USE_TZ = True


SOLANA_PAYMENTS = {
    "RPC_URL": "https://api.devnet.solana.com",
    "RECEIVER_ADDRESS": "9oH3Yw9o1u8k6rJ1sMZ9pL5m7f7y7bKz3rXGx9ZyQ1mA",
    "FEE_PAYER_ADDRESS": "11111111111111111111111111111111",
    "FEE_PAYER_KEYPAIR": "[1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56,57,58,59,60,61,62,63,64]",
    "ONE_TIME_WALLETS_ENCRYPTION_ENABLED": True,
    "ONE_TIME_WALLETS_ENCRYPTION_KEY": "v6EdqyuDAvh9dj9RQ-fGLqovy1KM4onalzw0Wl_EBE8=",
}
