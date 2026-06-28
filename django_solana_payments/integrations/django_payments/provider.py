import json
from decimal import Decimal
from typing import Any, Callable

from django.http import HttpResponseRedirect
from django.utils.module_loading import import_string
from payments import PaymentStatus
from payments.core import BasicProvider

from django_solana_payments.choices import SolanaPaymentStatusTypes, TokenTypes
from django_solana_payments.exceptions import (
    InvalidPaymentAmountError,
    PaymentExpiredError,
    PaymentNotConfirmedError,
    PaymentNotFoundError,
    PaymentTokenPriceNotFoundError,
)
from django_solana_payments.helpers import (
    get_payment_crypto_token_model,
    get_solana_payment_model,
)
from django_solana_payments.integrations.django_payments.forms import (
    SolanaWidgetPaymentForm,
)
from django_solana_payments.integrations.django_payments.utils import (
    build_payment_widget_config,
    build_solana_pay_url,
)
from django_solana_payments.services import (
    create_payment,
    verify_transaction_and_process_payment,
)
from django_solana_payments.settings import solana_payments_settings


class SolanaPaymentsProvider(BasicProvider):
    _method = "get"
    payment_state_attr = "solana_payment"

    def __init__(
        self,
        *,
        rpc_url: str | None = None,
        title: str = "Solana Payment",
        caption: str = "Scan the QR code using your wallet application on your mobile device",
        supported_wallets: list[str] | None = None,
        widget_js_path: str = "solana_payments/solana-payment-widget/widget.js",
        widget_css_path: str = "solana_payments/solana-payment-widget/widget.css",
        widget_theme: dict[str, Any] | None = None,
        wallet_adapter_factory: str | None = None,
        verify_poll_interval_ms: int = 1500,
        verify_timeout_ms: int = 45000,
        success_statuses: list[str] | None = None,
        payment_data_factory: str | Callable | None = None,
        token_selector: str | Callable | None = None,
        capture: bool = False,
    ) -> None:
        super().__init__(capture=capture)

        self.rpc_url = rpc_url or solana_payments_settings.RPC_URL
        self.title = title
        self.caption = caption
        self.supported_wallets = supported_wallets or ["phantom", "solflare"]
        self.widget_js_path = widget_js_path
        self.widget_css_path = widget_css_path
        self.widget_theme = widget_theme or {}
        self.wallet_adapter_factory = wallet_adapter_factory
        self.verify_poll_interval_ms = verify_poll_interval_ms
        self.verify_timeout_ms = verify_timeout_ms
        self.success_statuses = success_statuses or [
            "confirmed",
            "finalized",
            "processed",
        ]
        self.payment_data_factory = self._resolve_callable(payment_data_factory)
        self.token_selector = self._resolve_callable(token_selector)

    def _resolve_callable(self, value: str | Callable | None) -> Callable | None:
        if isinstance(value, str):
            return import_string(value)
        return value

    def get_form(self, payment, data=None):
        solana_payment = self._get_or_create_solana_payment(payment)
        token_price = self._select_token_price(
            payment=payment,
            solana_payment=solana_payment,
        )
        token = token_price.token
        amount = str(token_price.amount_in_crypto)
        label = self._build_payment_label(payment, solana_payment)
        message = self._build_payment_message(payment, solana_payment)
        spl_token = token.mint_address if token.token_type == TokenTypes.SPL else None
        token_prices = list(solana_payment.crypto_prices.select_related("token").all())
        ordered_token_prices = [token_price] + [
            price for price in token_prices if price.token.id != token_price.token.id
        ]

        widget_config = build_payment_widget_config(
            solana_pay_url=build_solana_pay_url(
                recipient=solana_payment.payment_address,
                amount=amount,
                label=label,
                message=message,
                spl_token=spl_token,
            ),
            rpc_url=self.rpc_url,
            recipient=solana_payment.payment_address,
            amount=amount,
            token_type=token.token_type,
            mint_address=token.mint_address,
            currency_symbol=getattr(token, "symbol", "SOL"),
            verify_endpoint=payment.get_process_url(),
            tokens={
                "initialTokens": [
                    {
                        "id": price.token.id,
                        "tokenType": price.token.token_type,
                        "mintAddress": price.token.mint_address,
                        "amount": str(price.amount_in_crypto),
                        "name": price.token.name,
                        "symbol": price.token.symbol,
                    }
                    for price in ordered_token_prices
                ],
            },
            title=self.title,
            caption=self.caption,
            supported_wallets=self.supported_wallets,
            wallet_adapter_factory=self.wallet_adapter_factory,
            poll_interval_ms=self.verify_poll_interval_ms,
            timeout_ms=self.verify_timeout_ms,
            success_statuses=self.success_statuses,
            theme=self.widget_theme,
        )
        self._store_payment_state(
            payment=payment,
            solana_payment=solana_payment,
            token=token,
            amount=amount,
            widget_config=widget_config,
        )

        return SolanaWidgetPaymentForm(
            payment=payment,
            widget_config=widget_config,
            widget_js_path=self.widget_js_path,
            widget_css_path=self.widget_css_path,
            mount_id=f"solana-payment-widget-{payment.token}",
        )

    def process_data(self, payment, request):
        state = self._get_payment_state(payment)
        payment_address = state.get("payment_address")
        if not payment_address:
            return self._redirect_error(
                payment=payment,
                detail="Solana payment is not linked to this django-solana_payments checkout.",
                payment_status=PaymentStatus.ERROR,
            )

        try:
            token = self._resolve_payment_token(state, request=request)
            transaction_status = verify_transaction_and_process_payment(
                payment_address=payment_address,
                payment_crypto_token=token,
                meta_data=self._build_verification_meta(payment, state),
            )
        except PaymentNotConfirmedError as exc:
            self._save_checkout_payment_status(
                payment,
                PaymentStatus.WAITING,
                str(exc),
            )
            return self._redirect_error(
                payment=payment,
                detail=str(exc) or "Payment has not yet been confirmed",
                payment_status=PaymentStatus.WAITING,
            )
        except PaymentExpiredError as exc:
            self._save_checkout_payment_status(
                payment,
                PaymentStatus.REJECTED,
                str(exc),
            )
            return self._redirect_success(
                redirect_url=payment.get_failure_url(),
            )
        except (PaymentNotFoundError, PaymentTokenPriceNotFoundError) as exc:
            return self._redirect_error(
                payment=payment,
                detail=str(exc) or "Payment not found",
                payment_status=PaymentStatus.ERROR,
            )
        except InvalidPaymentAmountError as exc:
            self._save_checkout_payment_status(
                payment,
                PaymentStatus.ERROR,
                str(exc),
            )
            return self._redirect_error(
                payment=payment,
                detail=str(exc),
                payment_status=PaymentStatus.ERROR,
            )

        checkout_status = self._map_solana_status_to_payment_status(transaction_status)
        self._save_checkout_payment_status(
            payment,
            checkout_status,
            str(transaction_status),
            captured_amount=(
                payment.total if checkout_status == PaymentStatus.CONFIRMED else None
            ),
        )
        redirect_url = (
            payment.get_success_url()
            if checkout_status == PaymentStatus.CONFIRMED
            else payment.get_failure_url()
        )
        return self._redirect_success(
            redirect_url=redirect_url,
        )

    def capture(self, payment, amount=None):
        raise NotImplementedError("Capture is not supported for Solana.")

    def release(self, payment):
        raise NotImplementedError("Release is not supported for Solana.")

    def refund(self, payment, amount=None):
        raise NotImplementedError(
            "Refund is not implemented. Handle treasury-side Solana refunds separately."
        )

    def cancel(self, payment):
        from payments import PaymentStatus

        state = self._get_payment_state(payment)
        solana_payment_id = state.get("solana_payment_id")
        if solana_payment_id:
            SolanaPayment = get_solana_payment_model()
            SolanaPayment.objects.filter(id=solana_payment_id).update(
                status=SolanaPaymentStatusTypes.EXPIRED
            )
        self._save_checkout_payment_status(
            payment,
            PaymentStatus.CANCELLED,
            "cancelled",
        )
        return None

    def _get_or_create_solana_payment(self, payment):
        state = self._get_payment_state(payment)
        solana_payment_id = state.get("solana_payment_id")
        SolanaPayment = get_solana_payment_model()

        if solana_payment_id:
            solana_payment = SolanaPayment.objects.filter(id=solana_payment_id).first()
            if solana_payment:
                return solana_payment

        payment_data = self._build_payment_data(payment)
        return create_payment(payment_data)

    def _build_payment_data(self, payment) -> dict[str, Any]:
        if self.payment_data_factory:
            return self.payment_data_factory(payment)

        description = payment.description or f"Payment {payment.token}"
        state = self._get_payment_state(payment)
        existing_meta = state.get("meta_data", {})

        return {
            "email": getattr(payment, "billing_email", "") or None,
            "label": description[:255],
            "message": description,
            "meta_data": {
                **existing_meta,
                "django_payment_token": str(payment.token),
                "django_payment_variant": payment.variant,
                "django_payment_total": str(payment.total),
                "django_payment_currency": payment.currency,
            },
        }

    def _select_token_price(self, *, payment, solana_payment):
        token_prices = list(solana_payment.crypto_prices.select_related("token").all())
        if not token_prices:
            raise ValueError(
                "No token prices are attached to the created Solana payment."
            )

        if self.token_selector:
            selected = self.token_selector(payment, solana_payment, token_prices)
            if selected is None:
                raise ValueError("token_selector returned no token price.")
            return selected

        return token_prices[0]

    def _build_payment_label(self, payment, solana_payment) -> str:
        return (
            getattr(solana_payment, "label", None)
            or payment.description
            or "Solana Payment"
        )[:255]

    def _build_payment_message(self, payment, solana_payment) -> str:
        return (
            getattr(solana_payment, "message", None)
            or payment.description
            or "Pay with a Solana-compatible wallet."
        )

    def _get_payment_state(self, payment) -> dict[str, Any]:
        try:
            extra_data = payment.extra_data or "{}"
            payload = json.loads(extra_data)
        except (TypeError, ValueError):
            payload = {}
        state = payload.get(self.payment_state_attr, {})
        return state if isinstance(state, dict) else {}

    def _store_payment_state(
        self,
        *,
        payment,
        solana_payment,
        token,
        amount: str,
        widget_config: dict,
    ) -> None:
        state = self._get_payment_state(payment)
        state.update(
            {
                "solana_payment_id": solana_payment.id,
                "payment_address": solana_payment.payment_address,
                "token_id": token.id,
                "token_type": token.token_type,
                "mint_address": token.mint_address,
                "amount": amount,
                "meta_data": solana_payment.meta_data or {},
                "widget_config": widget_config,
            }
        )
        setattr(payment.attrs, self.payment_state_attr, state)
        payment.transaction_id = solana_payment.payment_address
        payment.save(update_fields=["extra_data", "transaction_id"])

    def _resolve_payment_token(self, state: dict[str, Any], request=None):
        AllowedPaymentCryptoToken = get_payment_crypto_token_model()
        requested_mint_address = None
        if request is not None:
            requested_mint_address = request.GET.get(
                "mint_address"
            ) or request.POST.get("mint_address")
        mint_address = requested_mint_address or state.get("mint_address")
        if mint_address:
            token = AllowedPaymentCryptoToken.objects.filter(
                mint_address=mint_address, is_active=True
            ).first()
            if token:
                return token

        requested_token_type = None
        if request is not None:
            requested_token_type = request.GET.get("token_type") or request.POST.get(
                "token_type"
            )
        token_type = (
            requested_token_type or state.get("token_type") or TokenTypes.NATIVE
        )
        token = AllowedPaymentCryptoToken.objects.filter(
            token_type=token_type,
            is_active=True,
        ).first()
        if token:
            return token
        raise PaymentTokenPriceNotFoundError(mint_address or token_type)

    def _build_verification_meta(
        self,
        payment,
        state: dict[str, Any],
    ) -> dict[str, Any]:
        meta_data = state.get("meta_data", {})
        if not isinstance(meta_data, dict):
            meta_data = {}
        return {
            **meta_data,
            "django_payment_token": str(payment.token),
            "django_payment_variant": payment.variant,
            "django_payment_total": str(payment.total),
            "django_payment_currency": payment.currency,
        }

    def _map_solana_status_to_payment_status(self, solana_status: str):
        from payments import PaymentStatus

        if solana_status in {
            SolanaPaymentStatusTypes.CONFIRMED,
            SolanaPaymentStatusTypes.FINALIZED,
            SolanaPaymentStatusTypes.PROCESSED,
        }:
            return PaymentStatus.CONFIRMED
        if solana_status == SolanaPaymentStatusTypes.EXPIRED:
            return PaymentStatus.REJECTED
        return PaymentStatus.WAITING

    def _save_checkout_payment_status(
        self,
        payment,
        status: str,
        message: str,
        captured_amount: Decimal | None = None,
    ) -> None:
        update_fields = []
        if payment.status != status:
            payment.status = status
            update_fields.append("status")
        payment.message = message
        update_fields.append("message")
        if captured_amount is not None:
            payment.captured_amount = captured_amount
            update_fields.append("captured_amount")
        if update_fields:
            payment.save(update_fields=update_fields)

    def _redirect_success(
        self,
        redirect_url: str,
    ):
        return HttpResponseRedirect(redirect_url)

    def _redirect_error(
        self,
        payment,
        detail: str,
        payment_status: str,
    ):
        self._save_checkout_payment_status(
            payment,
            payment_status,
            detail,
        )
        return HttpResponseRedirect(payment.get_failure_url())
