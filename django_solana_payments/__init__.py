from typing import TYPE_CHECKING

from django_solana_payments.signals import (
    solana_payment_accepted,
    solana_payment_expired,
    solana_payment_initiated,
)

if TYPE_CHECKING:
    from django_solana_payments.services.one_time_wallet_service import (
        OneTimeWalletService,
    )
    from django_solana_payments.services.solana_payments_service import (
        SolanaPaymentsService,
    )
    from django_solana_payments.services.verify_transaction_service import (
        VerifyTransactionService,
    )


def create_one_time_wallet(should_create_atas: bool = True):
    from django_solana_payments.services import (
        create_one_time_wallet as _create_one_time_wallet,
    )

    return _create_one_time_wallet(should_create_atas=should_create_atas)


def create_payment(payment_data: dict):
    from django_solana_payments.services import create_payment as _create_payment

    return _create_payment(payment_data)


def verify_transaction_and_process_payment(
    payment_address: str,
    payment_crypto_token,
    meta_data=None,
    send_payment_accepted_signal: bool = True,
    on_success=None,
):
    from django_solana_payments.services import (
        verify_transaction_and_process_payment as _verify_transaction_and_process_payment,
    )

    return _verify_transaction_and_process_payment(
        payment_address=payment_address,
        payment_crypto_token=payment_crypto_token,
        meta_data=meta_data,
        send_payment_accepted_signal=send_payment_accepted_signal,
        on_success=on_success,
    )


def __getattr__(name: str):
    if name == "OneTimeWalletService":
        from django_solana_payments.services.one_time_wallet_service import (
            OneTimeWalletService,
        )

        return OneTimeWalletService
    if name == "SolanaPaymentsService":
        from django_solana_payments.services.solana_payments_service import (
            SolanaPaymentsService,
        )

        return SolanaPaymentsService
    if name == "VerifyTransactionService":
        from django_solana_payments.services.verify_transaction_service import (
            VerifyTransactionService,
        )

        return VerifyTransactionService
    raise AttributeError(f"module 'django_solana_payments' has no attribute {name!r}")


__all__ = [
    "OneTimeWalletService",
    "SolanaPaymentsService",
    "VerifyTransactionService",
    "create_one_time_wallet",
    "create_payment",
    "verify_transaction_and_process_payment",
    "solana_payment_accepted",
    "solana_payment_expired",
    "solana_payment_initiated",
]
