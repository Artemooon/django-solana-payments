# apps.py
from django.apps import AppConfig

class SolanaPayConfig(AppConfig):
    name = 'django_solana_payments'
    verbose_name = 'Solana Pay Integration'
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self):
        from .settings import solana_payments_settings
        # Trigger the property check to ensure RPC_URL exists
        _ = solana_payments_settings.SOLANA_RPC_URL
        _ = solana_payments_settings.SOLANA_RECEIVER_ADDRESS
