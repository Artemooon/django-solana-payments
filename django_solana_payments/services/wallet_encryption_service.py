import logging

from cryptography.fernet import Fernet, InvalidToken
from django.core.exceptions import ImproperlyConfigured
from solders.solders import Keypair

solana_logger = logging.getLogger(__name__)


class WalletEncryptionService:
    def __init__(self, encryption_key: str):
        try:
            self._fernet = Fernet(encryption_key.encode("utf-8"))
        except Exception as exc:
            raise ImproperlyConfigured(
                "Invalid ONE_TIME_WALLETS_ENCRYPTION_KEY"
            ) from exc

    def encrypt(self, plaintext: str) -> str:
        try:
            return self._fernet.encrypt(plaintext.encode("utf-8")).decode("utf-8")
        except Exception as e:
            solana_logger.error(f"Failed to encrypt wallet secret: {e}")
            raise ValueError(f"Encryption error: {e}")

    def decrypt(self, ciphertext: str) -> str:
        try:
            return self._fernet.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
        except InvalidToken:
            return Keypair.from_json(ciphertext)
        except Exception as e:
            solana_logger.error(f"Failed to decrypt wallet secret: {e}")
            raise ValueError(f"Decryption error: {e}")
