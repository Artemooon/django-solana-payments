.. _frontend_widget_configuration:

Frontend Widget Configuration
=============================

This page covers the frontend widget settings used by the reusable Solana payment widget.

If you are using the `django-payments` integration, these values are usually passed through your `PAYMENT_VARIANTS` config.
Check :doc:`django_payments_integration` for more details.

If you are mounting the widget directly, the same shape is used in the frontend widget config object.

The widget JavaScript and CSS files are shipped prebuilt inside the package under `django_solana_payments/static/...`.
For Django deployment, collect the packaged widget assets with:

.. code-block:: bash

    python manage.py collectstatic

After that, serve them through your standard Django static files setup.

.. _frontend_widget_recommended_api_driven_setup:

Recommended API-driven setup
----------------------------

If you include the package API routes, the simplest widget setup is to give the widget your API base URL and let it follow :ref:`DRF API integration flow <drf_api_integration_flow>`:

Example API-driven config:

.. code-block:: python

    widget_config = {
        "title": "Solana Payment",
        "caption": "Open a compatible wallet and scan the QR code.",
        "api": {
            "baseUrl": "/api/solana/",
            "initiatePayload": {
                "customer_id": "demo-customer",
                "label": "Order 1001",
                "message": "Demo payment",
            },
        },
        "wallet": {
            "enabled": True,
            "rpcUrl": "https://api.devnet.solana.com",
            "supportedWallets": ["phantom", "solflare"],
        },
        "verification": {
            "pollIntervalMs": 1500,
            "timeoutMs": 45000,
            "successStatuses": ["confirmed", "finalized", "processed"],
        },
    }

Example template:

.. code-block:: html

    {% load solana_payment_widget %}
    {% load solana_payment_widget_assets %}

    {% solana_payment_widget_assets %}

    {% render_solana_payment_widget widget_config "checkout-widget" %}

Manual asset inclusion:

.. code-block:: html

    {% load static %}
    {% load solana_payment_widget %}

    <link rel="stylesheet" href="{% static 'solana_payments/solana-payment-widget/widget.css' %}">

    {% render_solana_payment_widget widget_config "checkout-widget" %}

    <script type="module" src="{% static 'solana_payments/solana-payment-widget/widget.js' %}"></script>

Manual config shape:

.. code-block:: python

    widget_config = {
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

Frontend `widget_config` keys
-----------------------------

These settings belong to the frontend `widget_config` object:

- `api` (`dict`, optional): package API bootstrap settings. See `api` settings below.
- `solanaPayUrl` (`str`, optional): Solana Pay URL used for QR rendering. This is required only when you are not passing `transaction` or `api.baseUrl`. When `transaction` is present, the widget builds the Solana Pay URL on the frontend so the QR code stays in sync with the active token and amount.
- `title` (`str`, optional): widget heading. Defaults to `Solana Payment`.
- `caption` (`str`, optional): widget helper text under the title. Defaults to `Open a compatible wallet and scan the QR code.`.
- `mountId` (`str`, optional): mount element id. This is usually handled by the template tag, so you normally do not need to set it manually.
- `wallet` (`dict`, optional): wallet connection settings. See `wallet` settings below.
- `transaction` (`dict`, optional): transaction data used for wallet payments and Solana Pay URL rebuilding. This is required when neither `solanaPayUrl` nor `api.baseUrl` is provided. See `transaction` settings below.
- `tokens` (`dict`, optional): token selector configuration. See `tokens` settings below.
- `verification` (`dict`, optional): payment verification settings used after wallet submission. See `verification` settings below.
- `theme` (`dict`, optional): widget visual theme settings. See `theme` settings below.

You must provide at least one of:

- `api.baseUrl`
- `transaction`
- `solanaPayUrl`

`api` settings
--------------

- `baseUrl` (`str`, required when using `api`): base package API URL, for example `/api/solana/`.
- `initiatePayload` (`dict`, optional): JSON body sent to `POST <baseUrl>initiate/`. This is where you can pass values such as `customer_id`, `label`, `message`, or `meta_data`.

When `api.baseUrl` is present and `transaction` is omitted, the widget will call:

- `POST <baseUrl>initiate/`
- `GET <baseUrl>payments-tokens/`
- `GET <baseUrl>verify-transfer/<payment_address>`

`wallet` settings
-----------------

- `enabled` (`bool`, optional): enables the wallet action area. If omitted or false, the widget shows QR flow only.
- `rpcUrl` (`str`, required when `wallet.enabled` is true): Solana RPC endpoint used for wallet-based transaction building.
- `supportedWallets` (`list[str]`, optional): wallet names shown by the widget. Built-in values are `phantom` and `solflare`. You can also pass additional custom wallet names when using a custom adapter factory.
- `walletAdapterFactory` (`str`, optional): name of a frontend adapter factory registered on `window.SolanaPaymentWidget.adapterFactories`.

`transaction` settings
----------------------

- `recipient` (`str`, required): Solana recipient address.
- `label` (`str`, optional): label included in the Solana Pay URL.
- `message` (`str`, optional): message included in the Solana Pay URL.
- `amount` (`str`, required): payment amount as a decimal string.
- `tokenType` (`"NATIVE" | "SPL"`, optional): token type for wallet transaction building. Defaults to `NATIVE` when omitted.
- `mintAddress` (`str`, optional): SPL token mint address. Required when `tokenType` is `SPL`.
- `currencySymbol` (`str`, optional): display symbol for the active token. This is usually set automatically from the selected token option.

`tokens` settings
-----------------

Use `tokens` to add payment tokens to the widget token selector.

- `initialTokens` (`list[dict]`, optional): token options available in the selector. Each item uses the `token option` shape below.

`token option` settings
-----------------------

- `id` (`int`, required): unique token option id used by the selector.
- `tokenType` (`"NATIVE" | "SPL"`, required): token type for this option.
- `mintAddress` (`str | None`, optional): SPL token mint address. For native SOL, use `None` or omit it.
- `amount` (`str`, required): payment amount for this token option.
- `name` (`str`, required): display name, for example `Solana` or `USD Coin`.
- `symbol` (`str`, required): display symbol, for example `SOL` or `USDC`.

When you provide `tokens.initialTokens`, each token option should already contain its final payment `amount`.
If `initialTokens` is present, the selected token amount overrides `transaction.amount`.
The frontend widget treats `initialTokens` as a payment snapshot and does not refresh token data from the backend during widget lifetime.

Example `tokens` object:

.. code-block:: python

    "tokens": {
        "initialTokens": [
            {
                "id": 1,
                "tokenType": "NATIVE",
                "mintAddress": None,
                "amount": "0.015",
                "name": "Solana",
                "symbol": "SOL",
            },
            {
                "id": 2,
                "tokenType": "SPL",
                "mintAddress": "Es9vMFrzaCERmJfrF4H2FYD7P7C8XxYt3qYh3CwG4x4R",
                "amount": "1.25",
                "name": "USD Coin",
                "symbol": "USDC",
            },
        ],
    }

`verification` settings
-----------------------

- `enabled` (`bool`, optional): enables verification after wallet payment submission.
- `verifyEndpoint` (`str`, optional): verification endpoint URL. If omitted and `transaction.recipient` is present, the widget defaults to `/solana-payments/verify-transfer/<payment_address>/`.
- `redirectOnSuccess` (`bool`, optional): when true, the widget redirects the browser to the verification URL after a successful wallet submission instead of polling in place.
- `pollIntervalMs` (`int`, optional): polling interval in milliseconds. Defaults to `1500`.
- `timeoutMs` (`int`, optional): verification timeout in milliseconds. Defaults to `45000`.
- `successStatuses` (`list[str]`, optional): API statuses that should be treated as successful verification. Defaults to `["confirmed", "finalized", "processed"]`.

`theme` settings
----------------

- `accent` (`str`, optional): accent color.
- `background` (`str`, optional): widget background color.
- `text` (`str`, optional): primary text color.
- `mutedText` (`str`, optional): muted text color.
- `borderColor` (`str`, optional): border color.
- `borderRadius` (`str`, optional): border radius CSS value.
- `fontFamily` (`str`, optional): font family CSS value.
- `shadow` (`str`, optional): box shadow CSS value.
- `payButtonBackground` (`str`, optional): wallet pay button background color.
- `payButtonText` (`str`, optional): wallet pay button text color.
- `payButtonBorderColor` (`str`, optional): wallet pay button border color.
- `qrSize` (`int`, optional): QR code size in pixels. Defaults to `256`.


Asset path overrides
--------------------

These settings also belong to the backend `PAYMENT_VARIANTS` provider config.
In most setups you do not need to change them manually.

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
