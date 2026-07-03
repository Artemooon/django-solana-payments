from django.db import models
from django.urls import reverse
from payments.models import BasePayment

from django_solana_payments.models import AbstractPaymentToken, AbstractSolanaPayment


class CheckoutPayment(BasePayment):
    def get_success_url(self) -> str:
        return reverse("payment-success", kwargs={"token": self.token})

    def get_failure_url(self) -> str:
        return reverse("payment-failure", kwargs={"token": self.token})

    def get_purchased_items(self):
        return []


class CustomSolanaPayment(AbstractSolanaPayment):
    customer_id = models.CharField(max_length=255, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    label = models.CharField(max_length=255, blank=True, null=True)
    message = models.TextField(blank=True, null=True)
    # You can add any other custom fields here


class CustomPaymentToken(AbstractPaymentToken):
    name = models.CharField(max_length=100)
    symbol = models.CharField(max_length=10)
    # You can add any other custom fields here
