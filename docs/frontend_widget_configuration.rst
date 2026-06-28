.. _frontend_widget_configuration:

Frontend Widget Configuration
=============================

This page covers the frontend widget settings used by the reusable Solana payment widget.

If you are using the `django-payments` integration, these values are usually passed through your `PAYMENT_VARIANTS` config. If you are mounting the widget directly, the same shape is used in the frontend widget config object.

Common widget settings
----------------------

The widget reads these main groups:

- `wallet`: wallet connection settings
- `transaction`: payment recipient, amount, token type, and display details
- `tokens`: token selector data
- `verification`: how payment verification should work after the user sends the transaction
- `theme`: visual customization

Example `django-payments` setup
-------------------------------

.. code-block:: python

    PAYMENT_VARIANTS = {
        "solana": (
            "django_solana_payments.integrations.django_payments.SolanaPaymentsProvider",
            {
                "rpc_url": "https://api.devnet.solana.com",
                "tokens_endpoint": "/api/solana/payments-tokens/",
                "supported_wallets": ["phantom", "solflare"],
                "widget_js_path": "solana_payments/solana-payment-widget/widget.js",
                "widget_css_path": "solana_payments/solana-payment-widget/widget.css",
                "verify_poll_interval_ms": 1500,
                "verify_timeout_ms": 45000,
            },
        ),
    }

Widget parameters
-----------------

These are the settings you might want to tune:

- `rpc_url`: Solana RPC endpoint used by the widget wallet flow.
- `supported_wallets`: built-in wallet names the widget should show. The current built-in set is `phantom` and `solflare`.
- `tokens_endpoint`: endpoint the widget can call to load active payment tokens.
- `verify_poll_interval_ms`: polling interval used by the standalone widget verification flow.
- `verify_timeout_ms`: max time the standalone widget waits before showing a timeout.
- `widget_theme`: optional theme overrides for colors, radius, font, shadow, and QR size.

Asset path overrides
--------------------

In most setups you do not need to change the widget asset paths manually.

- `widget_js_path`: static path or full URL for the widget JavaScript bundle.
- `widget_css_path`: static path or full URL for the widget stylesheet.

These are mainly useful if you want to serve the widget bundle from a custom static location or a CDN. Otherwise it is better to keep the default generated paths.

About `success_statuses`
------------------------

`success_statuses` is only a frontend polling setting for the standalone widget flow.

It does not decide whether a payment is really successful. The backend remains the source of truth through the payment verification logic and the payment record itself, including fields like `status` and `expiration_date`.

In practice this setting just tells the widget which API response statuses should be treated as "verification succeeded, stop polling now".

If you are using the `django-payments` redirect flow, this setting is usually not something you need to tune.

About wallet adapters
---------------------

Today the built-in wallets are:

- `phantom`
- `solflare`

If you want to support more wallets, you can add them without editing the library code by using a custom adapter factory.

Custom wallet adapters
----------------------

Set a factory name in your provider config:

.. code-block:: python

    PAYMENT_VARIANTS = {
        "solana": (
            "django_solana_payments.integrations.django_payments.SolanaPaymentsProvider",
            {
                "supported_wallets": ["phantom", "solflare", "backpack"],
                "wallet_adapter_factory": "customSolanaAdapters",
            },
        ),
    }

Then register that factory in your frontend before the widget mounts:

.. code-block:: html

    <script type="module">
      import { BackpackWalletAdapter } from "@solana/wallet-adapter-backpack";

      window.SolanaPaymentWidget = window.SolanaPaymentWidget || {};
      window.SolanaPaymentWidget.adapterFactories =
        window.SolanaPaymentWidget.adapterFactories || {};

      window.SolanaPaymentWidget.adapterFactories.customSolanaAdapters = ({
        supportedWallets,
      }) => {
        const adapters = [];

        if (supportedWallets.includes("backpack")) {
          adapters.push(new BackpackWalletAdapter());
        }

        return adapters;
      };
    </script>

This way the library still handles the standard wallets, and your app only adds the extra adapters it actually needs.
