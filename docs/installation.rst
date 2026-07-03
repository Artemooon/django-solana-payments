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

2.  **Add the app to `INSTALLED_APPS`**

    .. code-block:: python

        INSTALLED_APPS = [
            ...,
            'django_solana_payments',
        ]

3.  **Create custom payment models**

    Create your own models that inherit from the library's abstract base models,
    then reference them from `SOLANA_PAYMENTS`.

    .. code-block:: python

        from django.db import models

        from django_solana_payments.models import (
            AbstractPaymentToken,
            AbstractSolanaPayment,
        )


        class CustomSolanaPayment(AbstractSolanaPayment):
            customer_id = models.CharField(max_length=255, blank=True, null=True)


        class CustomPaymentToken(AbstractPaymentToken):
            name = models.CharField(max_length=100)
            symbol = models.CharField(max_length=10)

    See :doc:`custom_models` for the full guide.

4.  **Configure `SOLANA_PAYMENTS`**

    After creating your models, point `SOLANA_PAYMENTS` at those model paths and
    configure the rest of the library settings.

    .. code-block:: python

        SOLANA_PAYMENTS = {
            "SOLANA_PAYMENT_MODEL": "solana_payments.CustomSolanaPayment", # Custom model for solana payment
            "PAYMENT_CRYPTO_TOKEN_MODEL": "solana_payments.CustomPaymentToken", # Custom model for solana payment token

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
            "RPC_COMMITMENT": "Confirmed", # RPC Commitment
            "PAYMENT_ACCEPTANCE_COMMITMENT": "Confirmed", # Commitment for payment acceptance
            "MAX_ATAS_PER_TX": 8, # Max associated token accounts to create/close per transaction
            "PAYMENT_VALIDITY_SECONDS": 30 * 60, # Payment validity window in seconds (default: 30 minutes)
        }

    If you need a better RPC control, use `BaseSolanaClient(client_factory=...)`.
    That allows specifying custom options for `AsyncClient`.

5.  **Migrate and Route**

    .. code-block:: bash

        python manage.py migrate

    .. code-block:: python

        # Add this to your urls.py
        urlpatterns = [
            path('solana-payments/', include('django_solana_payments.urls')),
        ]

6.  **Create payment tokens (required)**

    Open the admin panel and create at least one active payment token before initiating payments.
    A common setup is:

    - Native SOL token (`token_type=NATIVE`, `mint_address` empty)
    - USDC SPL token (`token_type=SPL`, with the correct USDC mint for your network)

    See :ref:`payment_tokens` for model fields, validation rules, and examples.

7.  **Continue with API usage**

    See :ref:`api_usage` for endpoint details and request examples.

Root level imports
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
