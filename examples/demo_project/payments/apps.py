from django.apps import AppConfig


class PaymentsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "payments"

    def ready(self):
        """
        Import signal handlers when the app is ready.
        This ensures the signal handlers are registered.
        """
        import payments.signals  # noqa: F401
