__all__ = [
    "SolanaPaymentsProvider",
    "SolanaWidgetPaymentForm",
]


def __getattr__(name: str):
    if name == "SolanaPaymentsProvider":
        from django_solana_payments.integrations.django_payments.provider import (
            SolanaPaymentsProvider,
        )

        return SolanaPaymentsProvider
    if name == "SolanaWidgetPaymentForm":
        from django_solana_payments.integrations.django_payments.forms import (
            SolanaWidgetPaymentForm,
        )

        return SolanaWidgetPaymentForm
    raise AttributeError(
        "module 'django_solana_payments.integrations.django_payments' "
        f"has no attribute {name!r}"
    )
