from django.db import models


class SolanaPaymentStatusTypes(models.TextChoices):
    INITIATED = "initiated"  # this status is assigned when user requested data to make a transfer
    FINALIZED = "finalized"
    CONFIRMED = "confirmed"
    PROCESSED = "processed"
    EXPIRED = "expired"


class OneTimeWalletStateTypes(models.TextChoices):
    CREATED = "created"
    RECEIVED_FUNDS = "received_funds"
    SENT_FUNDS = "sent_funds"
    PROCESSING_PAYMENT = "processing_payment"
    PROCESSING_FUNDS = "processing_funds"
    FAILED_TO_SEND_FUNDS = "failed_to_send_funds"
    PAYMENT_EXPIRED = "payment_expired"
    PAYMENT_EXPIRED_AND_WALLET_CLOSED = "payment_expired_and_wallet_closed"


class TokenTypes(models.TextChoices):
    NATIVE = "NATIVE", "Native"
    SPL = "SPL", "SPL Token"
