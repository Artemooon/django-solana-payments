import uuid

from django import template
from django.utils.html import format_html, json_script

register = template.Library()


@register.simple_tag
def render_solana_payment_widget(config: dict, mount_id: str = ""):
    resolved_mount_id = mount_id or f"solana-payment-widget-{uuid.uuid4().hex}"
    config_id = f"{resolved_mount_id}-config"
    return format_html(
        "{mount_node}{config_node}",
        mount_node=format_html(
            '<div id="{mount_id}" data-solana-payment-widget data-config-id="{config_id}"></div>',
            mount_id=resolved_mount_id,
            config_id=config_id,
        ),
        config_node=json_script(config, config_id),
        mount_id=resolved_mount_id,
        config_id=config_id,
    )
