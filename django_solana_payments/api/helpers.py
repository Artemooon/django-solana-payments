from rest_framework import serializers

from django_solana_payments.helpers import get_solana_payment_model


def get_initiate_solana_payment_serializer() -> type[serializers.Serializer]:
    SolanaPayment = get_solana_payment_model()

    class InitiateSolanaPaymentSerializer(serializers.ModelSerializer):
        class Meta:
            model = SolanaPayment
            fields = [
                field.name
                for field in SolanaPayment._meta.fields
                if field.name
                not in [
                    "id",
                    "payment_address",
                    "one_time_payment_wallet",
                    "paid_token",
                    "status",
                    "signature",
                    "expiration_date",
                    "created",
                    "updated",
                ]
            ]
            extra_kwargs = {
                field.name: {"required": False} for field in SolanaPayment._meta.fields
            }

    return InitiateSolanaPaymentSerializer
