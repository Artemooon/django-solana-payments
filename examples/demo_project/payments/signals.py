"""
Signal handlers for Solana payment events.

This module demonstrates how to use the solana_payment_accepted signal
to customize business logic when a payment is verified.
"""

import logging

from django.dispatch import receiver

from django_solana_payments.choices import SolanaPaymentStatusTypes
from django_solana_payments.signals import solana_payment_accepted

logger = logging.getLogger(__name__)


@receiver(solana_payment_accepted)
def handle_payment_accepted(
    sender, payment, transaction_status, payment_amount, **kwargs
):
    """
    Custom handler that fires when a Solana payment is successfully verified.

    This is where you can add your business logic:
    - Send confirmation emails
    - Update order status
    - Trigger webhooks
    - Grant access to paid content
    - Update user credits/balance
    - Log analytics events

    Args:
        sender: The class that sent the signal (VerifyTransactionService)
        payment: The SolanaPayment instance that was verified
        transaction_status: The transaction status (CONFIRMED or FINALIZED)
        **kwargs: Additional keyword arguments
    """
    payment_user = getattr(payment, "user", None)
    payment_label = getattr(payment, "label", None)

    logger.info(
        f"Payment accepted! Payment ID: {payment.id}, "
        f"Address: {payment.payment_address}, "
        f"Status: {transaction_status}, "
        f"User: {payment_user if payment_user else ''}"
    )

    # Example 1: Send email notification
    if payment_user and getattr(payment_user, "email", None):
        send_payment_confirmation_email(payment)

    # Example 2: Update related order status
    if payment.meta_data and "order_id" in payment.meta_data:
        update_order_status(payment.meta_data["order_id"], "paid")

    # Example 3: Grant premium access
    if payment_label == "Premium Subscription":
        grant_premium_access(payment_user)

    # Example 4: Log to analytics
    log_payment_to_analytics(payment, transaction_status)


def send_payment_confirmation_email(payment):
    """
    Send payment confirmation email to the user.

    In a real application, you would use Django's email backend or
    a service like SendGrid, Mailgun, etc.
    """
    payment_user = getattr(payment, "user", None)
    if not payment_user or not getattr(payment_user, "email", None):
        return

    logger.info(f"Sending confirmation email to {payment_user.email}")

    # Example implementation:
    # from django.core.mail import send_mail
    # send_mail(
    #     subject=f'Payment Confirmed - {payment.label}',
    #     message=f'Your payment of {payment.amount} has been confirmed.',
    #     from_email='noreply@yourapp.com',
    #     recipient_list=[payment_user.email],
    # )


def update_order_status(order_id, status):
    """
    Update the status of a related order.

    This assumes you have an Order model in your application.
    """
    logger.info(f"Updating order {order_id} to status: {status}")

    # Example implementation:
    # from your_app.models import Order
    # Order.objects.filter(id=order_id).update(status=status)


def grant_premium_access(user):
    """
    Grant premium access to the user.

    This could involve updating user profile, creating subscription records, etc.
    """
    if not user:
        return

    logger.info(f"Granting premium access to user {user.id}")

    # Example implementation:
    # user.profile.is_premium = True
    # user.profile.premium_until = timezone.now() + timedelta(days=30)
    # user.profile.save()


def log_payment_to_analytics(payment, transaction_status):
    """
    Log payment event to analytics service.

    You could integrate with Google Analytics, Mixpanel, Segment, etc.
    """
    logger.info(f"Logging payment {payment.id} to analytics")

    # Example implementation:
    # analytics.track(
    #     user_id=payment.user.id if payment.user else None,
    #     event='Payment Completed',
    #     properties={
    #         'payment_id': payment.id,
    #         'amount': str(payment.amount),
    #         'status': transaction_status,
    #         'label': payment.label,
    #     }
    # )


# Example: Handler that only runs for finalized transactions
@receiver(solana_payment_accepted)
def handle_finalized_payments_only(
    sender, payment, transaction_status, payment_amount, **kwargs
):
    """
    This handler only processes fully finalized transactions.

    Useful when you want to wait for maximum confirmation before taking action.
    """
    if transaction_status == SolanaPaymentStatusTypes.FINALIZED:
        logger.info(
            f"Payment {payment.id} is FINALIZED - processing irreversible actions"
        )

        # Perform actions that should only happen after finalization
        # For example: shipping physical goods, permanent account upgrades, etc.
