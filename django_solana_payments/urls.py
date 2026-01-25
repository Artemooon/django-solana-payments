"""
URL configuration for django_solana_payments project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.urls import path
from rest_framework.routers import SimpleRouter

from django_solana_payments.api.views.allowed_payment_crypto_token import (
    AllowedPaymentCryptoTokenViewSet,
)
from django_solana_payments.api.views.initiate_solana_payment import (
    InitiateSolanaPayment,
)
from django_solana_payments.api.views.solana_pay_payment import SolanaPaymentViewSet
from django_solana_payments.api.views.verify_transfer import VerifySolanaPayTransferView

router = SimpleRouter()
router.register("payments", SolanaPaymentViewSet)
router.register("payments-tokens", AllowedPaymentCryptoTokenViewSet)

urlpatterns = [
    path(
        "verify-transfer/<str:payment_address>", VerifySolanaPayTransferView.as_view()
    ),
    path("initiate/", InitiateSolanaPayment.as_view()),
]

urlpatterns += router.urls
