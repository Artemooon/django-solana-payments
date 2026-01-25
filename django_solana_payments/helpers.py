from typing import Type

from django.apps import apps
from django.core.exceptions import ImproperlyConfigured
from django_solana_payments.models import AbstractPaymentToken, AbstractSolanaPayment
from django_solana_payments.settings import solana_payments_settings


def get_payment_crypto_token_model() -> Type[AbstractPaymentToken]:
    model_name = solana_payments_settings.PAYMENT_CRYPTO_TOKEN_MODEL

    if not isinstance(model_name, str):
        raise ImproperlyConfigured(
            "PAYMENT_CRYPTO_TOKEN_MODEL must be a string of the form "
            "'app_label.ModelName'"
        )

    try:
        return apps.get_model(model_name)
    except ValueError:
        raise ImproperlyConfigured(
            "PAYMENT_CRYPTO_TOKEN_MODEL must be of the form "
            "'app_label.ModelName'"
        )
    except LookupError:
        raise ImproperlyConfigured(
            f"Model '{model_name}' referenced by "
            "PAYMENT_CRYPTO_TOKEN_MODEL could not be found"
        )


def get_solana_payment_model() -> Type[AbstractSolanaPayment]:
    model_name = solana_payments_settings.SOLANA_PAYMENT_MODEL

    if not isinstance(model_name, str):
        raise ImproperlyConfigured(
            "SOLANA_PAYMENT_MODEL must be a string of the form "
            "'app_label.ModelName'"
        )

    try:
        return apps.get_model(model_name)
    except ValueError:
        raise ImproperlyConfigured(
            "SOLANA_PAYMENT_MODEL must be of the form "
            "'app_label.ModelName'"
        )
    except LookupError:
        raise ImproperlyConfigured(
            f"Model '{model_name}' referenced by "
            "SOLANA_PAYMENT_MODEL could not be found"
        )


def get_solana_payment_related_name(field_name: str) -> str:
    """
    Dynamically resolves the related_name for a field on the SolanaPayment model.
    """
    SolanaPayment = get_solana_payment_model()
    field = SolanaPayment._meta.get_field(field_name)
    related_name = field.remote_field.related_name

    # The related_name might have placeholders like %(app_label)s and %(class)s
    if "%" in related_name:
        related_name = related_name % {
            "app_label": SolanaPayment._meta.app_label,
            "class": SolanaPayment._meta.model_name,
        }
    return related_name
