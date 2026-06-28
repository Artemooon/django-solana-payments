from django.apps import AppConfig


class SolanaPaymentsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "solana_payments"

    def ready(self):
        """
        Import signal handlers when the app is ready.
        This ensures the signal handlers are registered.
        """
        import solana_payments.signals  # noqa: F401
