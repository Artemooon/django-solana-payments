.. _payment_tokens:

Payment Tokens
==============

This page explains how to create and configure payment tokens that your project accepts. Payment tokens determine which cryptocurrencies (native SOL or SPL tokens) your project accepts and what amount (price) a payment should be in crypto units.

Token types and model fields
----------------------------

`django-solana-payments` exposes an abstract model `AbstractPaymentToken` and a concrete implementation `PaymentCryptoToken`.

Key fields (on `PaymentCryptoToken` / your custom token model):

- `is_active` (bool) — whether this token is currently accepted for payments.
- `token_type` (enum) — either `NATIVE` (SOL) or `SPL` (SPL token). Choose `SPL` when using a token mint address.
- `mint_address` (string) — required for `SPL` tokens, must be null for `NATIVE` tokens. The model enforces this via a database constraint.
- `payment_crypto_price` (Decimal) — the amount in crypto units that corresponds to a single payment for this token.
- `name`, `symbol`, `meta_data` — optional metadata fields on the concrete `PaymentCryptoToken`.

Important validation rules
--------------------------

- For `token_type == SPL`, `mint_address` is required.
- For `token_type == NATIVE`, `mint_address` must be null.

These rules are enforced by the model `clean()` method and by a database `CheckConstraint` on `PaymentCryptoToken`.

Database prerequisites
----------------------

1. Run migrations after you install the package or add your custom models:

.. code-block:: bash

    python manage.py makemigrations
    python manage.py migrate

2. If you use custom token models, make sure your custom app is included in `INSTALLED_APPS` and `SOLANA_PAYMENTS` settings points to your model path, for example::

    SOLANA_PAYMENTS = {
        "PAYMENT_CRYPTO_TOKEN_MODEL": "payments.CustomPaymentToken",
        # ... other settings
    }

Creating tokens (examples)
--------------------------

You can add tokens either through the Django admin or the Django shell.

- Via Admin

  Open the Django admin, find the `PaymentCryptoToken` (or your custom model) and create a new record. For SPL tokens provide the `mint_address` and set `is_active` to `True`.

- Via shell

.. code-block:: python

    # Start a shell
    python manage.py shell

    from django_solana_payments.models import PaymentCryptoToken

    # Native SOL token example
    PaymentCryptoToken.objects.create(
        name='SOL',
        symbol='SOL',
        token_type='NATIVE',
        payment_crypto_price=0.001,
        is_active=True,
    )

    # SPL token example
    PaymentCryptoToken.objects.create(
        name='MyToken',
        symbol='MTK',
        token_type='SPL',
        mint_address='TokenMintAddressHere',
        payment_crypto_price=10.0,
        is_active=True,
    )

Generating payment prices
-------------------------

The library provides a helper method on `SolanaPaymentsService` that will transform active `PaymentCryptoToken` records into `SolanaPayPaymentCryptoPrice` objects which are used when creating a `SolanaPayment`:

- `SolanaPaymentsService.create_payment_crypto_prices_from_allowed_payment_crypto_tokens()`

When you create a new payment using `SolanaPaymentsService.create_payment()` or the API endpoints, the service will automatically create and attach crypto price objects for the active tokens. You can also call the helper directly to pre-generate prices.

API and DRF
-----------

If you installed the `drf` extra, the library exposes a read-only endpoint for payment tokens at `/payments/payments-tokens/` (see `AllowedPaymentCryptoTokenViewSet`). Use that endpoint to list active tokens and their mint addresses.

Checklist before accepting payments
-----------------------------------

- [ ] Run migrations and confirm the `PaymentCryptoToken` table exists.
- [ ] Create at least one active token with valid fields (for SPL tokens set `mint_address`).
- [ ] If you use custom models, confirm `SOLANA_PAYMENTS["PAYMENT_CRYPTO_TOKEN_MODEL"]` points to the correct model path.
- [ ] Optionally, pre-generate crypto prices using `create_payment_crypto_prices_from_allowed_payment_crypto_tokens()` or let the service create them when you create payments.

Troubleshooting
---------------

- If you see a `ValidationError` when saving a token, verify the `token_type` and `mint_address` values match the rules described above.
- If the API shows no tokens, ensure `is_active=True` and the object is saved in the correct database and app.


