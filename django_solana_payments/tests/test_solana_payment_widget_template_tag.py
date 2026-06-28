import json
import re
from types import SimpleNamespace
from unittest.mock import patch

from django.template import Context, Engine


def _render_widget_tag(config: dict, mount_id: str | None = None) -> str:
    engine = Engine(
        libraries={
            "solana_payment_widget": (
                "django_solana_payments.templatetags.solana_payment_widget"
            )
        }
    )
    template_source = """
{% load solana_payment_widget %}
{% render_solana_payment_widget config mount_id %}
"""
    context = {"config": config, "mount_id": mount_id or ""}
    return engine.from_string(template_source).render(Context(context))


def _extract_json_script_content(rendered: str, script_id: str) -> dict:
    match = re.search(
        rf'<script id="{re.escape(script_id)}" type="application/json">(.*?)</script>',
        rendered,
        re.DOTALL,
    )
    assert match is not None
    return json.loads(match.group(1))


def test_render_solana_payment_widget_uses_explicit_mount_id():
    config = {
        "solanaPayUrl": "solana:abc123?amount=1",
        "theme": {"accent": "#0f766e"},
    }

    rendered = _render_widget_tag(config=config, mount_id="checkout-widget")

    assert 'id="checkout-widget"' in rendered
    assert "data-solana-payment-widget" in rendered
    assert 'data-config-id="checkout-widget-config"' in rendered
    assert _extract_json_script_content(rendered, "checkout-widget-config") == config


def test_render_solana_payment_widget_generates_mount_id_when_missing():
    config = {"title": "Pay with Solana"}

    with patch(
        "django_solana_payments.templatetags.solana_payment_widget.uuid.uuid4",
        return_value=SimpleNamespace(hex="generated123"),
    ):
        rendered = _render_widget_tag(config=config)

    assert 'id="solana-payment-widget-generated123"' in rendered
    assert 'data-config-id="solana-payment-widget-generated123-config"' in rendered
    assert (
        _extract_json_script_content(
            rendered,
            "solana-payment-widget-generated123-config",
        )
        == config
    )
