.. _management_commands:

Management Commands
===================

`django-solana-payments` provides commands to keep payment/wallet records healthy and to move funds from one-time wallets to your main wallet.

All commands support:

.. code-block:: bash

    --sleep <seconds>

Use `--sleep` to add a delay between blockchain operations and reduce rate-limit issues.

1. Expire Payments And Close Wallets
------------------------------------

**Command:**

.. code-block:: bash

    python manage.py close_expired_solana_payments_with_wallets

What it does:

- Marks expired `initiated` payments as `expired`.
- Tries to close related expired one-time wallets.

Example with delay:

.. code-block:: bash

    python manage.py close_expired_solana_payments_with_wallets --sleep 0.2

2. Send Funds From One-Time Wallets
-----------------------------------

**Command:**

.. code-block:: bash

    python manage.py send_solana_payments_from_one_time_wallets

What it does:

- Scans one-time wallets in processing/failed-send states.
- Sends available funds from one-time wallets to your configured receiver wallet.

Example with delay:

.. code-block:: bash

    python manage.py send_solana_payments_from_one_time_wallets --sleep 0.2

3. Close Expired Wallets And Reclaim Rent
-----------------------------------------

**Command:**

.. code-block:: bash

    python manage.py close_expired_one_time_wallets_and_reclaim_funds

What it does:

- Finds wallets in `PAYMENT_EXPIRED` state.
- Closes eligible associated token accounts (ATAs) to reclaim locked rent.

Example with delay:

.. code-block:: bash

    python manage.py close_expired_one_time_wallets_and_reclaim_funds --sleep 0.2

Recommended operations flow
---------------------------

For periodic maintenance jobs, a common order is:

1. `close_expired_solana_payments_with_wallets`
2. `send_solana_payments_from_one_time_wallets`
3. `close_expired_one_time_wallets_and_reclaim_funds`

You can run these manually, in cron, or via a task scheduler (Celery beat, systemd timers, etc.).
