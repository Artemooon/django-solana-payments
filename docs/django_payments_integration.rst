django-payments Integration
===========================

Install integration support with:

.. code-block:: bash

    pip install "django-solana-payments[django-payments]"

Configure the provider in `PAYMENT_VARIANTS`:

.. code-block:: python

    PAYMENT_VARIANTS = {
        "solana": (
            "django_solana_payments.integrations.django_payments.SolanaPaymentsProvider",
            {
                "rpc_url": "https://api.devnet.solana.com",
                "supported_wallets": ["phantom", "solflare"],
                "widget_js_path": "solana_payments/solana-payment-widget/widget.js",
                "widget_css_path": "solana_payments/solana-payment-widget/widget.css",
                "verify_poll_interval_ms": 1500,
                "verify_timeout_ms": 45000,
            },
        ),
    }

The provider creates or reuses `django-solana-payments` payment record, renders checkout widget,
and uses package verification flow during checkout processing.

Provider settings
-----------------

These settings belong to the backend `PAYMENT_VARIANTS` provider config:

- `rpc_url` (`str | None`): Solana RPC endpoint used by the widget wallet flow. If omitted, the provider falls back to the package settings value.
- `supported_wallets` (`list[str] | None`): built-in wallet names the widget should show. The current built-in set is `phantom` and `solflare`.
- `widget_js_path` (`str | None`): optional static path or full URL for the widget JavaScript bundle. If omitted, the provider uses the packaged default widget asset path.
- `widget_css_path` (`str | None`): optional static path or full URL for the widget stylesheet. If omitted, the provider uses the packaged default widget asset path.
- `widget_theme` (`dict[str, Any] | None`): optional theme overrides passed into the frontend widget theme config.
- `verify_poll_interval_ms` (`int`): polling interval used by the standalone widget verification flow.
- `verify_timeout_ms` (`int`): max time the standalone widget waits before showing a timeout.
- `success_statuses` (`list[str] | None`): verification API statuses that the frontend should treat as successful and stop polling on.

For frontend `widget_config` keys, direct widget mounting, verification defaults,
and custom wallet adapters, see :doc:`frontend_widget_configuration`.
