from django.db import transaction
from rest_framework import generics, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from django_solana_payments.api.serializers import (
    VerifySolanaPayTransferQuerySerializer,
    VerifySolanaPayTransferSerializer,
)
from django_solana_payments.exceptions import (
    InvalidPaymentAmountError,
    PaymentExpiredError,
    PaymentNotConfirmedError,
    PaymentNotFoundError,
    PaymentTokenPriceNotFoundError,
    ViewException,
)
from django_solana_payments.helpers import get_payment_crypto_token_model
from django_solana_payments.services.verify_transaction_service import (
    VerifyTransactionService,
)

AllowedPaymentCryptoToken = get_payment_crypto_token_model()


class VerifySolanaPayTransferView(generics.RetrieveAPIView):
    permission_classes = [AllowAny]
    serializer_class = VerifySolanaPayTransferSerializer

    @transaction.atomic
    def retrieve(self, request, *args, **kwargs):
        payment_address = self.kwargs.get("payment_address")

        query_serializer = VerifySolanaPayTransferQuerySerializer(
            data=request.query_params
        )
        query_serializer.is_valid(raise_exception=True)

        mint_address = query_serializer.validated_data.get("mint_address")
        token_type = query_serializer.validated_data["token_type"]

        if not payment_address:
            raise ViewException(
                "Reference is not provided", status_code=status.HTTP_400_BAD_REQUEST
            )

        if mint_address:
            payment_crypto_token = AllowedPaymentCryptoToken.objects.filter(
                is_active=True, mint_address=mint_address
            ).first()
        else:
            payment_crypto_token = AllowedPaymentCryptoToken.objects.filter(
                is_active=True, token_type=token_type
            ).first()

        if mint_address and not payment_crypto_token:
            raise ViewException(
                "Token is not supported. Check that provided mint_address exists in your PaymentCryptoToken model.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        try:
            verify_transaction_service = VerifyTransactionService()
            transaction_status = (
                verify_transaction_service.verify_transaction_and_process_payment(
                    payment_address=payment_address,
                    payment_crypto_token=payment_crypto_token,
                    meta_data=query_serializer.validated_data.get("meta_data"),
                )
            )
            serializer = self.serializer_class(
                data=dict(status=transaction_status, payment_address=payment_address)
            )

        except InvalidPaymentAmountError as exc:
            raise ViewException(
                error_message=str(exc),
                status_code=status.HTTP_409_CONFLICT,
            )
        except PaymentExpiredError as exc:
            raise ViewException(
                error_message=str(exc) or "Payment expired",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        except PaymentNotFoundError as exc:
            raise ViewException(
                error_message=str(exc) or "Payment not found",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        except PaymentTokenPriceNotFoundError as exc:
            raise ViewException(
                error_message=str(exc) or "Payment not found",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        except PaymentNotConfirmedError as exc:
            raise ViewException(
                error_message=str(exc) or "Payment not confirmed",
                status_code=status.HTTP_409_CONFLICT,
            )
        if not serializer.is_valid(raise_exception=False):
            raise ViewException(
                "Invalid status in response", status_code=status.HTTP_400_BAD_REQUEST
            )

        return Response(serializer.data)
