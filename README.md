# Django Solana Payments

![Documentation Status](https://app.readthedocs.org/projects/django-solana-payments/badge/?version=latest)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](https://github.com/Artemooon/django-solana-payments/blob/main/LICENSE)

A Django library for integrating Solana payments into your project. This library provides a flexible and customizable way to accept Solana payments with support for customizable models, an easy-to-use API, and management commands for processing online payments using the Solana blockchain.

## Key Features

-   **Flexibility and customization**: Use your own custom models for payments and tokens to fit your project's needs. Add custom logic using signals or callabacks.
-   **Ease of integration**: Provides ready-to-use endpoints that can be used in existing DRF applications, or ready-to-use methods for Django applications that are not part of DRF.
-   **Security and encryption**: Provides an out-of-the-box encryption mechanism that helps keep one-time payment wallets secure.
-   **Management commands**: Includes management commands for handling expired payments and sending funds from one-time wallets.

## Documentation

See the full documentation at https://django-solana-payments.readthedocs.io/

## Installation

1.  **Install the package**
    ```bash
    pip install django-solana-payments
    ```

    For DRF support, which provides API endpoints for creating and managing payments, install the `drf` extra:
    ```bash
    pip install "django-solana-payments[drf]"
    ```
    This provides ready-to-use API endpoints for creating and managing payments.

2.  **Configure `settings.py`**
    ```python
    INSTALLED_APPS = [
        ...,
        'django_solana_payments',
    ]

    SOLANA_PAYMENTS = {
        "RPC_URL": "https://api.mainnet-beta.solana.com",
        "RECEIVER_ADDRESS": "YOUR_WALLET_ADDRESS", # Wallet that receives funds
        "FEE_PAYER_KEYPAIR": "WALLET_KEYPAIR", # Wallet keypair that pays network fees (address will be derived from the keypair)
        # FEE_PAYER_ADDRESS is derived from FEE_PAYER_KEYPAIR; you don't normally need to set it separately.
        "ONE_TIME_WALLETS_ENCRYPTION_ENABLED": True, # Enables encryption for one-time payments wallets
        "ONE_TIME_WALLETS_ENCRYPTION_KEY": "ONE_TIME_WALLETS_ENCRYPTION_KEY", # Generate with the Fernet.generate_key()
        "SOLANA_PAYMENT_MODEL": "payments.CustomSolanaPayment", # Custom model for solana payment
        "PAYMENT_CRYPTO_TOKEN_MODEL": "payments.CustomPaymentToken", # Custom model for solana payment token
        "RPC_COMMITMENT": "Confirmed", # RPC Commitment
        "PAYMENT_ACCEPTANCE_COMMITMENT": "Confirmed", # Commitment for payment acceptance
        "MAX_ATAS_PER_TX": 8, # Max associated token accounts to create/close per transaction (needed for oen time wallets creation)
        "PAYMENT_VALIDITY_SECONDS": 30 * 60, # Payment validity window in seconds (default: 30 minutes)
    }
    ```

3.  **Migrate and Route**
```bash
python manage.py migrate
```

```python
# Add this to your urls.py
urlpatterns = [
    path('solana-payments/', include('django_solana_payments.urls')),
]
```

Open the admin panel and create payment token records, specifying the correct mint addresses for SPL tokens.


## Running the Example Project

The included example project provides a demonstration of how to use the library and what it can do. To run it:

1.  **Navigate to the example project directory**
    ```bash
    cd examples/demo_project
    ```

2.  **Install dependencies**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Run migrations**
    ```bash
    python mange.py makemigrations
    python manage.py migrate
    ```

4.  **Start the development server**
    ```bash
    ./dev_server.sh
    ```

## Running Tests

To run the tests for the library:

1.  **Install test dependencies**
    ```bash
    pip install pytest pytest-django
    ```

2.  **Run the tests**
    ```bash
    pytest
    ```

## License 

This package is licensed under the MIT License. See the LICENSE file for more details.

## Contributing

Contributions are welcome. If you encounter a bug, have a feature request, or see an opportunity for improvement, please open an issue to discuss it. Pull requests are also welcome.

If you find this project useful, consider giving it a star to support its development!
