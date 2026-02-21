.. _custom_models:

Custom Models
=============

`django-solana-payments` allows you to use your own custom models for Solana payments and payment tokens. This provides the flexibility to add extra fields and logic to suit your application's specific needs.

How it works
------------

The library uses abstract base classes, `AbstractSolanaPayment` and `AbstractPaymentToken`, which you can inherit from to create your own models. You then configure the library to use your custom models via the `SOLANA_PAYMENTS` dictionary in your `settings.py`.

Abstract base models reference
------------------------------

The two base classes are:

- :class:`django_solana_payments.models.AbstractPaymentToken`
- :class:`django_solana_payments.models.AbstractSolanaPayment`

You can see full API docs (including inherited fields/methods) in :ref:`api_reference`.

When you subclass them, you inherit required payment fields and behavior:

- `AbstractPaymentToken`: `is_active`, `token_type`, `mint_address`, `payment_crypto_price`, validation in `clean()`.
- `AbstractSolanaPayment`: `payment_address`, `one_time_payment_wallet`, `crypto_prices`, `paid_token`, `status`, `signature`, `expiration_date`, `meta_data`.

Creating Custom Models
----------------------

Here is an example of how to create custom models. In your app's `models.py` (e.g., `payments/models.py`):

.. code-block:: python

    from django.db import models
    from django_solana_payments.models import AbstractSolanaPayment, AbstractPaymentToken

    class CustomSolanaPayment(AbstractSolanaPayment):
        customer_id = models.CharField(max_length=255, blank=True, null=True)
        # You can add any other custom fields here

    class CustomPaymentToken(AbstractPaymentToken):
        name = models.CharField(max_length=100)
        symbol = models.CharField(max_length=10)
        # You can add any other custom fields here

In this example, `CustomSolanaPayment` adds a `customer_id` field, and `CustomPaymentToken` adds `name` and `symbol` fields.

Important notes for subclasses:

- Do not remove inherited fields required by the payment flow.
- Keep `token_type` and `mint_address` consistency rules intact (SPL requires `mint_address`, native SOL must not set it).
- Keep `payment_crypto_price` populated for active tokens, otherwise prices cannot be generated during payment initiation.

Configuring Settings
--------------------

After creating your custom models, you need to tell `django-solana-payments` to use them by updating your `settings.py`:

.. code-block:: python

    SOLANA_PAYMENTS = {
        # ... other settings
        "SOLANA_PAYMENT_MODEL": "payments.CustomSolanaPayment",
        "PAYMENT_CRYPTO_TOKEN_MODEL": "payments.CustomPaymentToken",
    }

Make sure to replace `"payments.CustomSolanaPayment"` and `"payments.CustomPaymentToken"` with the correct import paths for your models.

After configuring your settings, run migrations to create the tables for your new models:

.. code-block:: bash

    python manage.py makemigrations
    python manage.py migrate
