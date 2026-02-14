from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from solana.rpc.commitment import Commitment, Confirmed

from django_solana_payments.solana.utils import derive_pubkey_string_from_keypair


class SolanaPaymentsSettings:
    """
    Settings accessor for django-solana-payments.
    Reads from django.conf.settings.SOLANA_PAYMENTS dynamically.
    """

    def _get_setting(self, key, default=None, required=False):
        solana_config = getattr(settings, "SOLANA_PAYMENTS", {})
        value = solana_config.get(key, default)
        if required and value is None:
            raise ImproperlyConfigured(
                f"SOLANA_PAYMENTS['{key}'] is required in settings.py"
            )
        return value

    @property
    def SOLANA_RPC_URL(self) -> str:
        return self._get_setting("SOLANA_RPC_URL", required=True)

    @property
    def SOLANA_RECEIVER_ADDRESS(self) -> str:
        return self._get_setting("SOLANA_RECEIVER_ADDRESS", required=True)

    @property
    def RPC_CALLS_COMMITMENT(self) -> Commitment:
        return self._get_setting("RPC_CALLS_COMMITMENT", default=Confirmed)

    @property
    def PAYMENT_ACCEPTANCE_COMMITMENT(self) -> Commitment:
        return self._get_setting("PAYMENT_ACCEPTANCE_COMMITMENT", default=Confirmed)

    @property
    def SOLANA_FEE_PAYER_KEYPAIR(self) -> str | list | bytes:
        # New setting name replacing SOLANA_SENDER_KEYPAIR
        return self._get_setting("SOLANA_FEE_PAYER_KEYPAIR", required=True)

    @property
    def SOLANA_FEE_PAYER_ADDRESS(self) -> str:
        """
        Derive fee payer address (base58 string) from configured keypair using a shared parser.
        """
        fallback_address = self._get_setting("SOLANA_FEE_PAYER_ADDRESS")

        if fallback_address:
            return fallback_address

        keypair_data = self.SOLANA_FEE_PAYER_KEYPAIR
        try:
            # Use resilient derivation: returns real pubkey when possible, or a
            # deterministic fallback when given placeholder bytes/arrays (useful for tests).
            return derive_pubkey_string_from_keypair(keypair_data)
        except Exception as e:
            raise ImproperlyConfigured(
                "Invalid SOLANA_FEE_PAYER_KEYPAIR in settings. "
                "Supported formats: JSON string '[1,2,3,...]', Base58 string, or byte array. "
                f"Error: {e}"
                "Try to set SOLANA_FEE_PAYER_ADDRESS manually"
            )

    @property
    def ONE_TIME_WALLETS_ENCRYPTION_ENABLED(self) -> bool:
        return self._get_setting("ONE_TIME_WALLETS_ENCRYPTION_ENABLED", default=True)

    @property
    def ONE_TIME_WALLETS_ENCRYPTION_KEY(self) -> str:
        key = self._get_setting("ONE_TIME_WALLETS_ENCRYPTION_KEY", default=None)
        if self.ONE_TIME_WALLETS_ENCRYPTION_ENABLED and not key:
            raise ImproperlyConfigured(
                "ONE_TIME_WALLETS_ENCRYPTION_KEY must be set when "
                "ONE_TIME_WALLETS_ENCRYPTION_ENABLED=True"
            )
        return key

    @property
    def PAYMENT_VALIDITY_SECONDS(self) -> int:
        # Default to 30 minutes expressed in seconds
        return self._get_setting("PAYMENT_VALIDITY_SECONDS", default=30 * 60)

    @property
    def PAYMENT_CRYPTO_TOKEN_MODEL(self):
        return self._get_setting(
            "PAYMENT_CRYPTO_TOKEN_MODEL",
            default="django_solana_payments.PaymentCryptoToken",
        )

    @property
    def SOLANA_PAYMENT_MODEL(self):
        return self._get_setting(
            "SOLANA_PAYMENT_MODEL", default="django_solana_payments.SolanaPayment"
        )

    @property
    def MAX_ATAS_PER_TX(self) -> int:
        return self._get_setting("MAX_ATAS_PER_TX", default=8)


# Global instance - settings are read dynamically from django.conf.settings on each access
solana_payments_settings = SolanaPaymentsSettings()
