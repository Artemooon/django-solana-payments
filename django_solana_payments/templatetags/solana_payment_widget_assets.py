from django import template
from django.templatetags.static import static
from django.utils.html import format_html

register = template.Library()


@register.simple_tag
def solana_payment_widget_assets():
    css_url = static("solana_payments/solana-payment-widget/widget.css")
    js_url = static("solana_payments/solana-payment-widget/widget.js")

    return format_html(
        '<link rel="stylesheet" href="{css_url}">'
        '<script type="module" src="{js_url}"></script>',
        css_url=css_url,
        js_url=js_url,
    )
