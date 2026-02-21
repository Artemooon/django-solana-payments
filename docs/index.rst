.. django-solana-payments documentation master file, created by
   sphinx-quickstart on Sat Feb  7 19:50:48 2026.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to django-solana-payments's documentation!
==================================================

A plug-and-play Django library for accepting online payments via the Solana blockchain.

Key Features
------------

-   **Transaction verification and automatic payment confirmation**: Monitors the Solana blockchain, verifies incoming transactions, and automatically confirms payments when the expected amount is received.
-   **Multi-token support (SOL and SPL tokens)**: Configure a list of active payment tokens (for example, SOL and USDC) and the library will use them for pricing and verification flows.
-   **Flexibility and customization**: Use your own custom models for payments and tokens to fit your project's needs. Add custom logic using signals or callabacks.
-   **Ease of integration**: Provides ready-to-use endpoints that can be used in existing DRF applications, or ready-to-use methods for Django applications that are not part of DRF.
-   **Security and encryption**: Provides an out-of-the-box encryption mechanism that helps keep one-time payment wallets secure.
-   **Management commands**: Includes management commands for handling expired payments and sending funds from one-time wallets.

Security Note
-------------

`django-solana-payments` does not read or exfiltrate your provided wallet keypairs and has no external access to your secret keys or funds.
All wallet security controls, key management, maintenance policies, and security audits remain the responsibility of the user-facing application and its infrastructure.
See the full `Disclaimer <https://github.com/Artemooon/django-solana-payments/blob/main/DISCLAIMER.md>`_.

How It Works
------------

At its core, `django-solana-payments` works by creating a unique, one-time Solana wallet (keypairs) for each payment you want to receive.

For this reason you need to have some SOL balance on your `FEE_PAYER_KEYPAIR` wallet to pay transactions fess. Usually the cost is equals 0.000005 SOL which is default price to sign a transaction

These wallets metadata are stored in your database (with optional encryption for security, see :ref:`one_time_wallets_encryption`) and are linked to a specific payment record.

When a customer makes a payment, the library monitors the Solana blockchain for transactions sent to that unique one-time wallet.

By checking the balance and transaction history of this one-time wallet, the library can reliably verify when the correct amount has been paid and confirm the payment's status.

When you use non native tokens for payments library automatically creates `associated token address <https://www.solana-program.com/docs/associated-token-account>`_ which requires SOL for transactions fees (see details in Fees and chain costs section).

Payments have a validity period; after the time specified in the settings using PAYMENT_VALIDITY_SECONDS attribute, the payment status will expire and the payment will not be processed.

Fees and chain costs
------------
Base transaction fee for one-time wallet creation:

≈ SPL_TOKENS_AMOUNT × 0.00203 SOL (rent-exempt amount per ATA)
+ ~0.000005 SOL per transaction (network fee)

Where SPL_TOKENS_AMOUNT is the number of active PaymentToken instances (used SPL tokens).

Note that the final cost depends on the MAX_ATAS_PER_TX setting (8 ATAs per transaction by default).
If the number of active tokens exceeds MAX_ATAS_PER_TX, additional transactions will be required and each additional transaction will incur an extra network fee.

The rent-exempt amount is locked in the account and can be reclaimed by closing the ATA.

To reclaim funds manually, run the following command::

    python manage.py close_expired_one_time_wallets_and_reclaim_funds


django-solana-payments makes a best-effort attempt to minimize blockchain fee costs and to automate fund-reclaiming processes.
If you discover any additional ways to optimize costs, please let us know.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   installation
   drf_api_usage
   payment_tokens
   payment_confirmation_statuses
   custom_models
   payment_hooks
   management_commands
   one_time_wallets_encryption
   api_reference


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
