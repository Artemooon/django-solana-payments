from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from solana.rpc.commitment import Commitment, Confirmed


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
    def SOLANA_SENDER_KEYPAIR(self) -> str | list | bytes:
        return self._get_setting("SOLANA_SENDER_KEYPAIR", required=True)

    @property
    def SOLANA_SENDER_ADDRESS(self) -> str:
        return self._get_setting("SOLANA_SENDER_ADDRESS", required=True)

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
    def EXPIRATION_MINUTES(self) -> int:
        solana_config = getattr(settings, "SOLANA_PAYMENTS", {})
        return solana_config.get("EXPIRATION_MINUTES", 30)

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
