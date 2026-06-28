.. _installation:

Installation
============

1.  **Install the package**

    .. code-block:: bash

        pip install django-solana-payments

    For DRF support, which provides API endpoints for creating and managing payments, install the `drf` extra:

    .. code-block:: bash

        pip install "django-solana-payments[drf]"

    For `django-payments` integration support, install the `django-payments` extra:

    .. code-block:: bash

        pip install "django-solana-payments[django-payments]"

2.  **Configure `settings.py`**

    .. code-block:: python

        INSTALLED_APPS = [
            ...,
            'django_solana_payments',
        ]

        SOLANA_PAYMENTS = {
            "RPC_URL": "https://api.mainnet-beta.solana.com",
            "RECEIVER_ADDRESS": "YOUR_WALLET_ADDRESS", # Wallet that receives funds
            "FEE_PAYER_KEYPAIR": "WALLET_KEYPAIR", # Wallet keypair that pays network fees (address is derived from keypair)
            # FEE_PAYER_ADDRESS is derived from the keypair and doesn't need to be set separately
            "RPC_TIMEOUT": 10, # Optional AsyncClient timeout in seconds
            "RPC_EXTRA_HEADERS": None, # Optional dict of extra RPC headers
            "RPC_PROXY": None, # Optional proxy URL
            "RPC_RATE_LIMIT": 0, # Optional AsyncClient rate limit; 0 disables limiter
            "ONE_TIME_WALLETS_ENCRYPTION_ENABLED": True, # Enables encryption for one-time payments wallets
            "ONE_TIME_WALLETS_ENCRYPTION_KEY": "ONE_TIME_WALLETS_ENCRYPTION_KEY", # Generate with the Fernet.generate_key()
            "SOLANA_PAYMENT_MODEL": "solana_payments.CustomSolanaPayment", # Custom model for solana payment
            "PAYMENT_CRYPTO_TOKEN_MODEL": "solana_payments.CustomPaymentToken", # Custom model for solana payment token
            "RPC_COMMITMENT": "Confirmed", # RPC Commitment
            "PAYMENT_ACCEPTANCE_COMMITMENT": "Confirmed", # Commitment for payment acceptance
            "MAX_ATAS_PER_TX": 8, # Max associated token accounts to create/close per transaction
            "PAYMENT_VALIDITY_SECONDS": 30 * 60, # Payment validity window in seconds (default: 30 minutes)
        }

    If you need a better RPC control, use `BaseSolanaClient(client_factory=...)`.
    That allows specifying custom options for `AsyncClient`.

3.  **Migrate and Route**

    .. code-block:: bash

        python manage.py migrate

    .. code-block:: python

        # Add this to your urls.py
        urlpatterns = [
            path('solana-payments/', include('django_solana_payments.urls')),
        ]

4.  **Create payment tokens (required)**

    Open the admin panel and create at least one active payment token before initiating payments.
    A common setup is:

    - Native SOL token (`token_type=NATIVE`, `mint_address` empty)
    - USDC SPL token (`token_type=SPL`, with the correct USDC mint for your network)

    See :ref:`payment_tokens` for model fields, validation rules, and examples.

5.  **Continue with API usage**

    See :ref:`api_usage` for endpoint details and request examples.

Convenience imports
-------------------

For common flows you can import the root helpers directly:

.. code-block:: python

    from django_solana_payments import (
        create_payment,
        verify_transaction_and_process_payment,
    )

    payment = create_payment(
        {
            "label": "Premium Plan",
            "message": "Monthly subscription",
            "meta_data": {"order_id": "sub-1001"},
        }
    )

    status = verify_transaction_and_process_payment(
        payment_address=payment.payment_address,
        payment_crypto_token=my_token,
    )

For explicit service classes, see :doc:`api_reference`.

For async-capable usage and `AsyncClient` details, see :doc:`async_support`.
