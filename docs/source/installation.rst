.. _installation:

Installation
============

1.  **Install the package**

    .. code-block:: bash

        pip install django-solana-payments

    For DRF support, which provides API endpoints for creating and managing payments, install the `drf` extra:

    .. code-block:: bash

        pip install django-solana-payments[drf]

2.  **Configure `settings.py`**

    .. code-block:: python

        INSTALLED_APPS = [
            ...,
            'django_solana_payments',
        ]

        SOLANA_PAYMENTS = {
            "RPC_URL": "https://api.mainnet-beta.solana.com",
            "RECEIVER_ADDRESS": "YOUR_WALLET_ADDRESS", # Wallet that receives funds
            "SOLANA_FEE_PAYER_KEYPAIR": "WALLET_KEYPAIR", # Wallet keypair that pays network fees (address is derived from keypair)
            # SOLANA_FEE_PAYER_ADDRESS is derived from the keypair and doesn't need to be set separately
            "ONE_TIME_WALLETS_ENCRYPTION_ENABLED": True, # Enables encryption for one-time payments wallets
            "ONE_TIME_WALLETS_ENCRYPTION_KEY": "ONE_TIME_WALLETS_ENCRYPTION_KEY",
            "SOLANA_PAYMENT_MODEL": "payments.CustomSolanaPayment", # Custom model for solana payment
            "PAYMENT_CRYPTO_TOKEN_MODEL": "payments.CustomPaymentToken", # Custom model for solana payment token
            "RPC_CALLS_COMMITMENT": "Confirmed", # RPC Commitment
            "PAYMENT_ACCEPTANCE_COMMITMENT": "Confirmed", # Commitment for payment acceptance
            "MAX_ATAS_PER_TX": 8, # Max associated token accounts to create/close per transaction
            "PAYMENT_VALIDITY_SECONDS": 30 * 60, # Payment validity window in seconds (default: 30 minutes)
        }

3.  **Migrate and Route**

    .. code-block:: bash

        python manage.py migrate

    .. code-block:: python

        # Add this to your urls.py
        urlpatterns = [
            path('payments/', include('django_solana_payments.urls')),
        ]

    Open the admin panel and create payment token records, specifying the correct mint addresses for SPL tokens.
    See :ref:`payment_tokens` for model fields, validation rules, and examples.

    After routing, see :ref:`api_usage` for endpoint details and request examples.