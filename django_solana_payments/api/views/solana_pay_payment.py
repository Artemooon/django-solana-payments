from django.db.models import Prefetch

from django_solana_payments.api.serializers import SolanaPaymentSerializer
from django_solana_payments.helpers import get_solana_payment_model
from django_solana_payments.models import SolanaPayPaymentCryptoPrice
from rest_framework.mixins import RetrieveModelMixin
from rest_framework.permissions import AllowAny
from rest_framework.viewsets import GenericViewSet

SolanaPayment = get_solana_payment_model()


class SolanaPaymentViewSet(GenericViewSet, RetrieveModelMixin):
    pagination_class = None
    queryset = SolanaPayment.objects.prefetch_related(
        Prefetch(
        "crypto_prices",
            queryset=SolanaPayPaymentCryptoPrice.objects.select_related("token"),
        )
    ).all()
    serializer_class = SolanaPaymentSerializer
    permission_classes = [AllowAny]
    lookup_field = "payment_address"
