.. _frontend_widget_configuration:

Frontend Widget Configuration
=============================

This page covers the frontend widget settings used by the reusable Solana payment widget.

If you are using the `django-payments` integration, these values are usually passed through your `PAYMENT_VARIANTS` config. If you are mounting the widget directly, the same shape is used in the frontend widget config object.

Direct widget setup without `django-payments`
---------------------------------------------

You can use the frontend widget in a regular Django page without `django-payments`.

Typical setup:

1. Build a `widget_config` dict in your view.
2. Render widget markup in your template.
3. Include the widget CSS and JavaScript assets.

Example template:

.. code-block:: html

    {% load static %}
    {% load solana_payment_widget %}

    <link rel="stylesheet" href="{% static 'solana_payments/solana-payment-widget/widget.css' %}">

    {% render_solana_payment_widget widget_config "checkout-widget" %}

    <script type="module" src="{% static 'solana_payments/solana-payment-widget/widget.js' %}"></script>

Example config shape:

.. code-block:: python

    widget_config = {
        "solanaPayUrl": "solana:RECIPIENT_ADDRESS?amount=1.5&label=Order%201001",
        "title": "Solana Payment",
        "caption": "Open a compatible wallet and scan the QR code.",
        "wallet": {
            "enabled": True,
            "rpcUrl": "https://api.devnet.solana.com",
            "supportedWallets": ["phantom", "solflare"],
        },
        "transaction": {
            "recipient": "RECIPIENT_ADDRESS",  # for example, payment.payment_address from create_payment(...)
            "amount": "1.5",  # fallback/default amount, for example str(token_prices[0].amount_in_crypto) when no token selector overrides it
            "tokenType": "NATIVE",
            "label": "Order 1001",
            "message": "Demo payment",
        },
        "tokens": {},
        "verification": {
            "enabled": True,
            "verifyEndpoint": "/solana-payments/verify-transfer/RECIPIENT_ADDRESS/",
            "pollIntervalMs": 1500,
            "timeoutMs": 45000,
            "successStatuses": ["confirmed", "finalized"],
        },
    }

The template tag renders widget mount node and serialized config for you.
If you prefer, you can generate the same markup manually, but using the tag is simpler.

When you provide `tokens.initialTokens`, each token option should carry its own `amount`.
In that case the widget uses selected token amount for QR code and wallet transaction building.
`transaction.amount` acts as fallback/default transaction amount.

Example `tokens` object
-----------------------

Use `tokens` when you want widget token selector enabled.

.. code-block:: python

    "tokens": {
        "initialTokens": [
            {
                "id": 1,
                "tokenType": "NATIVE",
                "mintAddress": None,
                "amount": "0.015",  # for example, str(token_prices[0].amount_in_crypto)
                "name": "Solana",
                "symbol": "SOL",
            },
            {
                "id": 2,
                "tokenType": "SPL",
                "mintAddress": "Es9vMFrzaCERmJfrF4H2FYD7P7C8XxYt3qYh3CwG4x4R",
                "amount": "1.25",  # for example, str(token_prices[1].amount_in_crypto)
                "name": "USD Coin",
                "symbol": "USDC",
            },
        ],
    }

Notes:

- `initialTokens` should already contain actual payment amounts for each token option.
- If `initialTokens` is present, selected token amount overrides `transaction.amount` inside widget flow.
- The frontend widget uses `initialTokens` as payment snapshot. It does not refresh token data from backend during widget lifetime.

Verification defaults
---------------------

If you mount widget directly, passing verification config is optional.
The frontend widget can use default verification flow when `transaction.recipient` is present.

Typical package route:

.. code-block:: python

    "verification": {
        "enabled": True,
        "verifyEndpoint": f"/solana-payments/verify-transfer/{payment.payment_address}/",
        "pollIntervalMs": 1500,
        "timeoutMs": 45000,
        "successStatuses": ["confirmed", "finalized", "processed"],
    }

If `verification.verifyEndpoint` is omitted but `transaction.recipient` is present,
the frontend widget defaults to:

.. code-block:: text

    /solana-payments/verify-transfer/<payment_address>/

That path matches package default route when you include:

.. code-block:: python

    path("solana-payments/", include("django_solana_payments.urls"))

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
