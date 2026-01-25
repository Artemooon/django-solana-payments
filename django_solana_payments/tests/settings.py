import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent

load_dotenv()

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
    "SOLANA_RPC_URL": "https://api.devnet.solana.com",
    "SOLANA_RECEIVER_ADDRESS": "9oH3Yw9o1u8k6rJ1sMZ9pL5m7f7y7bKz3rXGx9ZyQ1mA",
    "SOLANA_SENDER_KEYPAIR": os.environ.get("SOLANA_SENDER_KEYPAIR"),
    "SOLANA_SENDER_ADDRESS": os.environ.get("SOLANA_SENDER_ADDRESS"),
    "ONE_TIME_WALLETS_ENCRYPTION_ENABLED": True,
    "ONE_TIME_WALLETS_ENCRYPTION_KEY": "v6EdqyuDAvh9dj9RQ-fGLqovy1KM4onalzw0Wl_EBE8=",
}
