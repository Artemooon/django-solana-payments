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

For widget-related options such as wallet settings, asset paths, verification behavior,
and custom wallet adapters, see :doc:`frontend_widget_configuration`.
