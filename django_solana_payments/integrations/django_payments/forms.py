import uuid

from django.template.loader import render_to_string
from django.templatetags.static import static
from django.utils.safestring import mark_safe
from payments.forms import PaymentForm


class SolanaWidgetPaymentForm(PaymentForm):
    default_template_name = (
        "django_solana_payments/integrations/django_payments/widget_form.html"
    )

    def __init__(
        self,
        *,
        payment,
        widget_config: dict,
        widget_js_path: str,
        widget_css_path: str,
        template_name: str = default_template_name,
        mount_id: str = "",
    ) -> None:
        super().__init__(
            data=None,
            action=payment.get_process_url(),
            method="get",
            payment=payment,
            hidden_inputs=False,
        )
        self.payment = payment
        self.widget_config = widget_config
        self.widget_js_path = widget_js_path
        self.widget_css_path = widget_css_path
        self.widget_template_name = template_name
        self.mount_id = mount_id or f"solana-payment-widget-{uuid.uuid4().hex}"
        self.widget_js_url = self._resolve_asset_url(widget_js_path)
        self.widget_css_url = self._resolve_asset_url(widget_css_path)

    def _resolve_asset_url(self, path: str) -> str:
        if path.startswith(("http://", "https://", "/")):
            return path
        return static(path)

    def get_context(self) -> dict:
        return {
            "form": self,
            "payment": self.payment,
        }

    def render(self) -> str:
        return render_to_string(self.widget_template_name, self.get_context())

    def __html__(self) -> str:
        return mark_safe(self.render())

    def __str__(self) -> str:
        return self.__html__()
