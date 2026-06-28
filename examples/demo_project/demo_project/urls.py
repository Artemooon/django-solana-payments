"""
URL configuration for demo_project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
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

from django.contrib import admin
from django.urls import include, path
from solana_payments.views import (
    checkout,
    payment_details,
    payment_failure,
    payment_success,
    widget_demo,
    widget_demo_editorial,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", widget_demo, name="widget-demo"),
    path("themes/editorial/", widget_demo_editorial, name="widget-demo-editorial"),
    path("django-payments/", checkout, name="django-payments-checkout"),
    path("payments/", include("payments.urls")),
    path("django-payments/<uuid:token>/", payment_details, name="payment-details"),
    path(
        "django-payments/<uuid:token>/success/", payment_success, name="payment-success"
    ),
    path(
        "django-payments/<uuid:token>/failure/", payment_failure, name="payment-failure"
    ),
    path("api/solana/", include("django_solana_payments.urls")),
]
