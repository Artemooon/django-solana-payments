from django_solana_payments.api.serializers import AllowedCryptoTokenSerializer
from django_solana_payments.helpers import get_payment_crypto_token_model
from rest_framework.permissions import AllowAny
from rest_framework.viewsets import ReadOnlyModelViewSet

AllowedPaymentCryptoToken = get_payment_crypto_token_model()

class AllowedPaymentCryptoTokenViewSet(ReadOnlyModelViewSet):
    queryset = AllowedPaymentCryptoToken.objects.filter(is_active=True)
    serializer_class = AllowedCryptoTokenSerializer
    permission_classes = [AllowAny]
