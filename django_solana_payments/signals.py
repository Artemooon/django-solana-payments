from django.dispatch import Signal

# Fired when a payment row is created in INITIATED status.
solana_payment_initiated = Signal()

# Fired when a payment moves to EXPIRED status.
solana_payment_expired = Signal()

# Fired when a payment is successfully verified.
solana_payment_accepted = Signal()
