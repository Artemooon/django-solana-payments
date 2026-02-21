Payment Confirmation Statuses
=============================

`django-solana-payments` uses Solana commitment levels to decide when a payment is considered verified and accepted.

Two settings are important:

- `RPC_COMMITMENT`: commitment level used for general RPC reads.
- `PAYMENT_ACCEPTANCE_COMMITMENT`: commitment level required before the library marks a payment as accepted.

Example configuration::

    SOLANA_PAYMENTS = {
        "RPC_COMMITMENT": Confirmed,
        "PAYMENT_ACCEPTANCE_COMMITMENT": Finalized,
    }

Commitment levels
-----------------

- `Processed`: fastest, lowest safety. Transaction is seen by a node but may still be rolled back.
- `Confirmed`: safer than `Processed`, usually good for many real-time flows.
- `Finalized`: safest option. Best for high-assurance payment verification, but takes longer.

