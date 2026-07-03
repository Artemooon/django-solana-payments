from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.csrf import ensure_csrf_cookie
from payments import PaymentStatus, get_payment_model
from solana_payments.widget_config import build_payment_widget_config

Payment = get_payment_model()

DEFAULT_WIDGET_THEME = {
    "accent": "#0f766e",
    "background": "#f8fafc",
    "text": "#111827",
    "mutedText": "#475569",
    "borderColor": "#cbd5e1",
    "borderRadius": "20px",
    "fontFamily": '"Helvetica Neue", Arial, sans-serif',
    "shadow": "0 18px 40px rgba(15, 23, 42, 0.08)",
    "payButtonBackground": "#0f8a83",
    "payButtonText": "#ffffff",
    "payButtonBorderColor": "#0f8a83",
    "qrSize": 256,
}

EDITORIAL_WIDGET_THEME = {
    "accent": "#a33b24",
    "background": "#f7efe4",
    "text": "#26170f",
    "mutedText": "#725645",
    "borderColor": "#d7c1ab",
    "borderRadius": "28px",
    "fontFamily": '"Georgia", "Times New Roman", serif',
    "shadow": "0 22px 44px rgba(87, 53, 30, 0.14)",
    "payButtonBackground": "#26170f",
    "payButtonText": "#f7efe4",
    "payButtonBorderColor": "#26170f",
    "qrSize": 256,
}


def get_widget_asset_version() -> str:
    static_root = (
        Path(__file__).resolve().parent
        / "static"
        / "solana_payments"
        / "solana-payment-widget"
    )
    asset_paths = (
        static_root / "widget.js",
        static_root / "widget.css",
    )
    existing_paths = [path for path in asset_paths if path.exists()]
    if not existing_paths:
        return "dev"

    latest_mtime = max(path.stat().st_mtime_ns for path in existing_paths)
    return str(latest_mtime)


def _render_widget_demo(
    request,
    *,
    theme: dict,
    theme_name: str,
    page_title: str,
    page_description: str,
):
    default_label = request.GET.get("label", "Demo payment")
    default_message = request.GET.get("message", "Scan with a Solana Pay wallet")
    api_base_url = reverse("initiate-payment").removesuffix("initiate/")

    widget_config = build_payment_widget_config(
        api_base_url=api_base_url,
        rpc_url=settings.SOLANA_PAYMENTS["RPC_URL"],
        initiate_payload={
            "customer_id": request.GET.get("customer_id", "demo-customer"),
            "label": default_label,
            "message": default_message,
        },
        verification={
            "pollIntervalMs": 1500,
            "timeoutMs": 45000,
            "successStatuses": ["confirmed", "finalized", "processed"],
        },
        theme=theme,
        title=page_title,
        caption="Scan the QR code using your wallet application on your mobile device",
    )
    return render(
        request,
        "solana_payments/widget_demo.html",
        {
            "widget_config": widget_config,
            "widget_asset_version": get_widget_asset_version(),
            "theme_name": theme_name,
            "page_title": page_title,
            "page_description": page_description,
        },
    )


@ensure_csrf_cookie
def widget_demo(request):
    return _render_widget_demo(
        request,
        theme=DEFAULT_WIDGET_THEME,
        theme_name="Default",
        page_title="Solana Payment",
        page_description=(
            "Clean teal checkout styling for the reusable Solana widget."
        ),
    )


@ensure_csrf_cookie
def widget_demo_editorial(request):
    return _render_widget_demo(
        request,
        theme=EDITORIAL_WIDGET_THEME,
        theme_name="Editorial",
        page_title="Collector Checkout",
        page_description=(
            "Warm editorial styling with serif typography and a softer card treatment."
        ),
    )


def checkout(request):
    payment = Payment.objects.create(
        variant="solana",
        status=PaymentStatus.WAITING,
        total=Decimal("10.00"),
        currency="USD",
        description="Test order",
    )
    return redirect("payment-details", token=payment.token)


def payment_details(request, token):
    payment = get_object_or_404(Payment, token=token)
    form = payment.get_form(data=request.GET or None)
    return render(
        request, "solana_payments/payment.html", {"payment": payment, "form": form}
    )


def payment_success(request, token):
    payment = get_object_or_404(Payment, token=token)
    return render(
        request,
        "solana_payments/payment_result.html",
        {"payment": payment, "result": "success"},
    )


def payment_failure(request, token):
    payment = get_object_or_404(Payment, token=token)
    return render(
        request,
        "solana_payments/payment_result.html",
        {"payment": payment, "result": "failure"},
    )
