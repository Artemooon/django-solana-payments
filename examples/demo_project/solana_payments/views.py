from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from payments import PaymentStatus, get_payment_model
from solana_payments.widget_config import (
    build_payment_widget_config,
    build_solana_pay_url,
)

from django_solana_payments import create_payment
from django_solana_payments.choices import TokenTypes
from django_solana_payments.exceptions import PaymentConfigurationError

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
    payment = None
    error_message = None
    solana_pay_url = ""
    default_label = request.GET.get("label", "Demo payment")
    default_message = request.GET.get("message", "Scan with a Solana Pay wallet")
    token = None
    token_prices = []
    tokens_endpoint = request.build_absolute_uri("/api/solana/payments-tokens/")

    try:
        payment = create_payment(
            {
                "customer_id": request.GET.get("customer_id", "demo-customer"),
            }
        )
        token_prices = list(
            payment.crypto_prices.select_related("token").order_by("id")
        )
        if not token_prices:
            raise PaymentConfigurationError(
                "No payment crypto prices were created for the demo payment."
            )

        payment_price = token_prices[0]
        token = payment_price.token
        spl_token = (
            token.mint_address
            if token.token_type == TokenTypes.SPL and token.mint_address
            else None
        )
        solana_pay_url = build_solana_pay_url(
            recipient=payment.payment_address,
            amount=str(payment_price.amount_in_crypto),
            label=getattr(payment, "label", None) or default_label,
            message=getattr(payment, "message", None) or default_message,
            spl_token=spl_token,
        )
    except Exception as exc:
        error_message = str(exc)

    widget_config = build_payment_widget_config(
        solana_pay_url=solana_pay_url,
        rpc_url=settings.SOLANA_PAYMENTS["RPC_URL"],
        transaction={
            "recipient": payment.payment_address if payment else "",
            "amount": str(token_prices[0].amount_in_crypto) if token_prices else "",
            "label": (
                (getattr(payment, "label", None) or default_label)
                if payment
                else default_label
            ),
            "message": (
                (getattr(payment, "message", None) or default_message)
                if payment
                else default_message
            ),
            "tokenType": token.token_type if token else TokenTypes.NATIVE,
            "mintAddress": token.mint_address if token else None,
            "currencySymbol": getattr(token, "symbol", "SOL") if token else "SOL",
        },
        tokens={
            "endpoint": tokens_endpoint,
            "initialTokens": [
                {
                    "id": price.token.id,
                    "tokenType": price.token.token_type,
                    "mintAddress": price.token.mint_address,
                    "amount": str(price.amount_in_crypto),
                    "name": price.token.name,
                    "symbol": price.token.symbol,
                }
                for price in token_prices
            ],
        },
        verification={
            "enabled": bool(payment),
            "verifyEndpoint": (
                reverse(
                    "verify-transfer",
                    kwargs={"payment_address": payment.payment_address},
                )
                if payment
                else ""
            ),
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
            "solana_pay_url": solana_pay_url,
            "payment": payment,
            "error_message": error_message,
            "theme_name": theme_name,
            "page_title": page_title,
            "page_description": page_description,
        },
    )


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
