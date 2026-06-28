from typing import TYPE_CHECKING, Any, Callable

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


def create_payment(payment_data: dict):
    from django_solana_payments.services.solana_payments_service import (
        SolanaPaymentsService,
    )

    return SolanaPaymentsService().create_payment(payment_data)


def create_one_time_wallet(should_create_atas: bool = True):
    from django_solana_payments.services.one_time_wallet_service import (
        one_time_wallet_service,
    )

    return one_time_wallet_service.create_one_time_wallet(
        should_create_atas=should_create_atas
    )


def verify_transaction_and_process_payment(
    payment_address: str,
    payment_crypto_token,
    meta_data: dict[str, Any] | None = None,
    send_payment_accepted_signal: bool = True,
    on_success: Callable | None = None,
):
    from django_solana_payments.services.verify_transaction_service import (
        VerifyTransactionService,
    )

    return VerifyTransactionService().verify_transaction_and_process_payment(
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
    raise AttributeError(
        f"module 'django_solana_payments.services' has no attribute {name!r}"
    )


__all__ = [
    "OneTimeWalletService",
    "SolanaPaymentsService",
    "VerifyTransactionService",
    "create_one_time_wallet",
    "create_payment",
    "verify_transaction_and_process_payment",
]
