.. django-solana-payments documentation master file, created by
   sphinx-quickstart on Sat Feb  7 19:50:48 2026.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to django-solana-payments's documentation!
==================================================

A plug-and-play Django library for accepting online payments via the Solana blockchain.

Key Features
------------

-   **Flexibility and customization**: Use your own custom models for payments and tokens to fit your project's needs. Add custom logic using signals or callabacks
-   **Ease of integration**: Provides ready-to-use endpoints that can be used in existing DRF applications, or ready-to-use methods for Django applications that are not part of DRF.
-   **Management commands**: Includes management commands for handling expired payments and sending funds from one-time wallets.
-   **Security and encryption**: Provides an out-of-the-box encryption mechanism that helps keep one-time payment wallets secure

How It Works
------------

At its core, `django-solana-payments` works by creating a unique, one-time Solana wallet (keypairs) for each payment you want to receive.

For this reason you need to have some SOL balance on your `SOLANA_SENDER_KEYPAIR` wallet to pay transactions fess. Usually the cost is equals 0.000005 SOL which is default price to sign a transaction

These wallets metadata are stored in your database (with optional encryption for security) and are linked to a specific payment record.

When a customer makes a payment, the library monitors the Solana blockchain for transactions sent to that unique wallet.

By checking the balance and transaction history of this one-time wallet, the library can reliably verify when the correct amount has been paid and confirm the payment's status, all without needing to manage complex webhook systems.

When you use non native tokens for payments library automatically creates `associated token address <https://www.solana-program.com/docs/associated-token-account>`_ which requires

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
   custom_models
   payment_hooks
   api_reference


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
