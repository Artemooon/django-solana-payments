from django.db import transaction
from rest_framework import generics
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from django_solana_payments.api.helpers import get_initiate_solana_payment_serializer
from django_solana_payments.services.solana_payments_service import (
    SolanaPaymentsService,
)


class InitiateSolanaPayment(generics.CreateAPIView):
    permission_classes = [AllowAny]
    serializer_class = get_initiate_solana_payment_serializer()

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        payment_data = serializer.validated_data
        if request.user.is_authenticated:
            payment_data["user"] = request.user

        payment = SolanaPaymentsService().create_payment(payment_data)

        return Response(
            {"payment_address": payment.payment_address},
            status=201,
        )
