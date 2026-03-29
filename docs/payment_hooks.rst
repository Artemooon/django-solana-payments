.. _payment_hooks:

Payment Hooks
=============

`django-solana-payments` provides hooks that allow you to add your own custom logic to the payment verification process. You can use either Django's signaling system or a direct callback function.

This is useful for tasks like:
- Sending confirmation emails
- Updating order statuses
- Granting access to content or features
- Logging events to analytics

Using Signals
-------------

The library exposes a small set of lifecycle signals for durable payment state changes. This is the recommended way to attach your own logic if you are using the DRF plugin and do not want to override views or services.

Available signals:

- **`solana_payment_initiated`**: fired after a payment row is created in `INITIATED` status.
- **`solana_payment_expired`**: fired after a payment is moved to `EXPIRED` status.
- **`solana_payment_accepted`**: fired after a payment is successfully verified and processed.

Signal payloads:

**`solana_payment_initiated`**
- `sender`: `SolanaPaymentsService`
- `payment`: the created payment instance
- `transaction_status`: always `INITIATED`

**`solana_payment_expired`**
- `sender`: `SolanaPaymentsService` or `VerifyTransactionService`, depending on which flow expired the payment
- `payment`: the expired payment instance
- `transaction_status`: always `EXPIRED`

**`solana_payment_accepted`**
- `sender`: `VerifyTransactionService`
- `payment`: the verified payment instance
- `transaction_status`: the accepted payment status (`CONFIRMED` or `FINALIZED`; `PROCESSED` may also appear if your acceptance commitment is configured that way)
- `payment_amount`: the amount of cryptocurrency that was paid

Signals are dispatched with `send_robust()` and scheduled with `transaction.on_commit()` where relevant, so receivers do not break payment processing and only run after the DB transaction is committed.

The package does not currently emit a generic "payment failed" signal. Most verification failures in the current flow are transient or request-level outcomes, not durable payment lifecycle states.

**Example Signal Handler:**

Here is an example of how you can define signal handlers in your project. You can place this code in a `signals.py` file inside one of your apps.

.. code-block:: python

    import logging
    from django.dispatch import receiver
    from django_solana_payments.signals import (
        solana_payment_accepted,
        solana_payment_expired,
        solana_payment_initiated,
    )
    from django_solana_payments.choices import SolanaPaymentStatusTypes

    logger = logging.getLogger(__name__)

    @receiver(solana_payment_initiated)
    def handle_payment_initiated(sender, payment, transaction_status, **kwargs):
        logger.info(
            "Payment initiated: id=%s status=%s address=%s",
            payment.id,
            transaction_status,
            payment.payment_address,
        )

    @receiver(solana_payment_accepted)
    def handle_payment_accepted(
        sender,
        payment,
        transaction_status,
        payment_amount=None,
        **kwargs,
    ):
        """
        Custom handler that fires when a Solana payment is verified.
        """
        logger.info(
            "Payment accepted: id=%s status=%s amount=%s",
            payment.id,
            transaction_status,
            payment_amount,
        )

        # Example 1: Send a confirmation email
        if payment.user and payment.user.email:
            send_payment_confirmation_email(payment)

        # Example 2: Update a related order
        if payment.meta_data and "order_id" in payment.meta_data:
            update_order_status(payment.meta_data["order_id"], "paid")

    @receiver(solana_payment_expired)
    def handle_payment_expired(
        sender,
        payment,
        transaction_status,
        **kwargs,
    ):
        logger.warning(
            "Payment expired: id=%s status=%s",
            payment.id,
            transaction_status,
        )

    def send_payment_confirmation_email(payment):
        logger.info(f"Sending confirmation email to {payment.user.email}")
        # Add your email sending logic here

    def update_order_status(order_id, status):
        logger.info(f"Updating order {order_id} to status: {status}")
        # Add your order update logic here


Remember to import your signals in your app's `apps.py` file to ensure they are registered:

.. code-block:: python

    # your_app/apps.py
    from django.apps import AppConfig

    class YourAppConfig(AppConfig):
        name = 'your_app'

        def ready(self):
            import your_app.signals  # noqa

All examples can be found in the `demo project <https://github.com/Artemooon/django-solana-payments/blob/main/examples/demo_project/payments/signals.py>`_

Using the `on_success` Callback
-------------------------------

If you are calling the verification service directly, you can pass an `on_success` callback function.

The callback receives the `payment` instance and the `transaction_status`.

Current behavior:

- the callback only runs for successful verification flows
- it is scheduled with `transaction.on_commit()`
- it runs after the payment row is committed
- if `send_payment_accepted_signal=True`, the success signal is attempted before the callback
- callback exceptions are logged and do not roll back the payment update

**Example `on_success` Callback:**

.. code-block:: python

    from django_solana_payments.services import VerifyTransactionService

    def my_success_callback(payment, transaction_status):
        print(f"Payment {payment.id} was successful with status {transaction_status}!")
        # Add any other custom logic here

    # When calling the service
    verify_service = VerifyTransactionService()
    verify_service.verify_transaction_and_process_payment(
         payment_address="...",
         payment_crypto_token=my_token,
         on_success=my_success_callback
    )

This approach is useful for synchronous tasks or when you want to handle the logic in the same part of the code that initiates the verification.
