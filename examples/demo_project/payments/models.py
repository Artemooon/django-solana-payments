from django.db import models
from django_solana_payments.models import AbstractSolanaPayment, AbstractPaymentToken


class CustomSolanaPayment(AbstractSolanaPayment):
    customer_id = models.CharField(max_length=255, blank=True, null=True)
    # You can add any other custom fields here


class CustomPaymentToken(AbstractPaymentToken):
    name = models.CharField(max_length=100)
    symbol = models.CharField(max_length=10)
    # You can add any other custom fields here
