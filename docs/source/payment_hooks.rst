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

The library sends a `solana_payment_accepted` signal when a payment is successfully verified and processed. You can listen for this signal to trigger your custom logic.

The signal provides the following arguments:
- `sender`: The class that sent the signal (`VerifyTransactionService`).
- `payment`: The payment instance that was verified.
- `transaction_status`: The confirmation status of the transaction (e.g., `CONFIRMED` or `FINALIZED`).
- `payment_amount`: The amount of cryptocurrency that was paid.

**Example Signal Handler:**

Here is an example of how you can define signal handlers in your project. You can place this code in a `signals.py` file inside one of your apps.

.. code-block:: python

    import logging
    from django.dispatch import receiver
    from django_solana_payments.signals import solana_payment_accepted
    from django_solana_payments.choices import SolanaPaymentStatusTypes

    logger = logging.getLogger(__name__)

    @receiver(solana_payment_accepted)
    def handle_payment_accepted(sender, payment, transaction_status, **kwargs):
        """
        Custom handler that fires when a Solana payment is verified.
        """
        logger.info(
            f"Payment accepted! Payment ID: {payment.id}, "
            f"Status: {transaction_status}"
        )

        # Example 1: Send a confirmation email
        if payment.user and payment.user.email:
            send_payment_confirmation_email(payment)

        # Example 2: Update a related order
        if payment.meta_data and "order_id" in payment.meta_data:
            update_order_status(payment.meta_data["order_id"], "paid")

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

Using the `on_success` Callback
-------------------------------

If you are calling the verification service directly, you can pass an `on_success` callback function. This function will be executed after the payment is successfully verified and before the signal is sent.

The callback receives the `payment` instance and the `transaction_status` as arguments.

**Example `on_success` Callback:**

.. code-block:: python

    from django_solana_payments.services import VerifyTransactionService

    def my_success_callback(payment, transaction_status):
        print(f"Payment {payment.id} was successful with status {transaction_status}!")
        # Add any other custom logic here

    # When calling the service
    # verify_service = VerifyTransactionService()
    # verify_service.verify_transaction_and_process_payment(
    #     payment_address="...",
    #     payment_crypto_token=my_token,
    #     on_success=my_success_callback
    # )

This approach is useful for synchronous tasks or when you want to handle the logic in the same part of the code that initiates the verification.

