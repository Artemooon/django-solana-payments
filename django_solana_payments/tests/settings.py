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
    "SOLANA_RECEIVER_ADDRESS": os.environ.get("SOLANA_RECEIVER_ADDRESS"),
    "SOLANA_SENDER_KEYPAIR": os.environ.get("SOLANA_SENDER_KEYPAIR"),
    "SOLANA_SENDER_ADDRESS": os.environ.get("SOLANA_SENDER_ADDRESS"),
    "ONE_TIME_WALLETS_ENCRYPTION_ENABLED": True,
    "ONE_TIME_WALLETS_ENCRYPTION_KEY": "CK8u9nHAkt-UUf2nZLjLxHp2YoLqkap7oM9s2tO7QiE="
}