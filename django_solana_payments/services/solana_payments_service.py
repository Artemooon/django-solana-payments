import logging
import time

from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from solders.solders import Pubkey

from django_solana_payments.choices import (
    OneTimeWalletStateTypes,
    SolanaPaymentStatusTypes,
)
from django_solana_payments.exceptions import PaymentConfigurationError, PaymentError
from django_solana_payments.helpers import (
    get_payment_crypto_token_model,
    get_solana_payment_model,
    get_solana_payment_related_name,
)
from django_solana_payments.models import (
    OneTimePaymentWallet,
    SolanaPayPaymentCryptoPrice,
)
from django_solana_payments.services.main_wallet_service import (
    send_transaction_and_update_one_time_wallet,
)
from django_solana_payments.services.one_time_wallet_service import (
    one_time_wallet_service,
)
from django_solana_payments.services.verify_transaction_service import (
    VerifyTransactionService,
)
from django_solana_payments.settings import solana_payments_settings
from django_solana_payments.solana.base_solana_client import base_solana_client
from django_solana_payments.solana.enums import TransactionTypeEnum
from django_solana_payments.solana.solana_balance_client import SolanaBalanceClient

logger = logging.getLogger(__name__)

AllowedPaymentCryptoToken = get_payment_crypto_token_model()
SolanaPayment = get_solana_payment_model()


class SolanaPaymentsService:
    def recheck_initiated_payments_and_process(
        self,
        limit: int | None = None,
        sleep_interval_seconds: float | int | None = None,
        send_payment_accepted_signal: bool = True,
        on_success=None,
    ) -> dict[str, int]:
        """
        Recheck INITIATED payments against on-chain state and process missed confirmations.

        This recovery flow is intended for cases where users paid to one-time wallets but
        the original verification flow did not update DB status in time.
        """
        queryset = SolanaPayment.objects.filter(
            status=SolanaPaymentStatusTypes.INITIATED
        ).prefetch_related("crypto_prices__token")

        if limit:
            payments = list(queryset.order_by("-updated")[:limit])
        else:
            payments = list(queryset.order_by("-updated"))

        verify_service = VerifyTransactionService()
        scanned = 0
        reconciled = 0
        pending = 0
        failed = 0
        skipped_no_tokens = 0

        for payment in payments:
            scanned += 1

            token_prices = list(payment.crypto_prices.select_related("token").all())
            if not token_prices:
                skipped_no_tokens += 1
                continue

            payment_reconciled = False
            payment_failed = False

            for price in token_prices:
                token = getattr(price, "token", None)
                if not token:
                    continue

                try:
                    status = verify_service.verify_transaction_and_process_payment(
                        payment_address=payment.payment_address,
                        payment_crypto_token=token,
                        send_payment_accepted_signal=send_payment_accepted_signal,
                        on_success=on_success,
                    )
                except PaymentError as exc:
                    logger.info(
                        "Recheck payment_id=%s token_id=%s skipped: %s",
                        payment.id,
                        token.id,
                        str(exc),
                    )
                    continue
                except Exception as exc:
                    logger.exception(
                        "Recheck failed unexpectedly for payment_id=%s token_id=%s: %s",
                        payment.id,
                        token.id,
                        exc,
                    )
                    payment_failed = True
                    break

                if status in {
                    SolanaPaymentStatusTypes.CONFIRMED,
                    SolanaPaymentStatusTypes.FINALIZED,
                    SolanaPaymentStatusTypes.PROCESSED,
                }:
                    payment_reconciled = True
                    break

            if payment_reconciled:
                reconciled += 1
            elif payment_failed:
                failed += 1
            else:
                pending += 1

            if sleep_interval_seconds:
                time.sleep(sleep_interval_seconds)

        return {
            "scanned": scanned,
            "reconciled": reconciled,
            "pending": pending,
            "failed": failed,
            "skipped_no_tokens": skipped_no_tokens,
        }

    def check_expired_solana_payments(self):
        expired_payments = SolanaPayment.objects.filter(
            status=SolanaPaymentStatusTypes.INITIATED,
            expiration_date__lte=timezone.now(),
        )
        total_not_finished_payments = expired_payments.count()
        logger.info(
            "Total not finished solana payments: %s", total_not_finished_payments
        )

        if total_not_finished_payments == 0:
            return

        expired_payments.update(status=SolanaPaymentStatusTypes.EXPIRED)

        wallet_ids = expired_payments.filter(
            one_time_payment_wallet__isnull=False
        ).values_list("one_time_payment_wallet__id", flat=True)

        OneTimePaymentWallet.objects.filter(id__in=list(wallet_ids)).update(
            state=OneTimeWalletStateTypes.PAYMENT_EXPIRED
        )

        logger.info(
            "Marked %s expired payments and their wallets.",
            total_not_finished_payments,
        )

    def mark_not_finished_solana_payments_as_expired_and_close_wallets_accounts(
        self, sleep_interval_seconds: float | int | None = None
    ):
        logger.info("Starting Solana cleanup task...")

        try:
            logger.info("Step 1: Checking and expiring Solana payments")
            self.check_expired_solana_payments()
        except Exception as e:
            logger.warning(f"⚠ Error during check_expired_solana_payments: {e}")

        try:
            logger.info("Step 2: Closing expired one-time wallets")
            one_time_wallet_service.close_expired_one_time_wallets(
                sleep_interval_seconds
            )
        except Exception as e:
            logger.warning(f"⚠ Error during close_expired_one_time_wallets: {e}")

        logger.info("Solana cleanup task finished.")

    def send_solana_payments_from_one_time_wallets(
        self, sleep_interval_seconds: float | int | None = None
    ):
        payment_wallet_related_name = get_solana_payment_related_name(
            "one_time_payment_wallet"
        )
        paid_token_related_path = f"{payment_wallet_related_name}__paid_token"

        one_time_wallets_with_balance = OneTimePaymentWallet.objects.select_related(
            payment_wallet_related_name, paid_token_related_path
        ).filter(
            Q(state=OneTimeWalletStateTypes.PROCESSING_PAYMENT)
            | Q(state=OneTimeWalletStateTypes.PROCESSING_FUNDS)
            | Q(state=OneTimeWalletStateTypes.FAILED_TO_SEND_FUNDS)
        )

        count = one_time_wallets_with_balance.count()
        logger.info("Found %s one-time wallets to process.", count)

        if count == 0:
            return

        solana_balance_client = SolanaBalanceClient(
            base_solana_client=base_solana_client
        )

        for wallet in one_time_wallets_with_balance:
            wallet_keypair = one_time_wallet_service.load_keypair(wallet.keypair_json)
            wallet_address = wallet_keypair.pubkey()
            recipient_address = solana_payments_settings.RECEIVER_ADDRESS
            logger.info(
                "Processing one-time wallet id=%s address=%s recipient=%s",
                wallet.id,
                wallet_address,
                recipient_address,
            )

            if sleep_interval_seconds:
                time.sleep(sleep_interval_seconds)  # To prevent rate limiting
            balance_sol = solana_balance_client.get_balance_by_address(wallet_address)
            logger.info("Wallet id=%s SOL balance=%s", wallet.id, balance_sol)

            payment = getattr(wallet, payment_wallet_related_name)
            paid_token = payment.paid_token

            balance_spl = (
                solana_balance_client.get_spl_token_balance_by_address(
                    wallet_address, Pubkey.from_string(paid_token.mint_address)
                )
                if paid_token and paid_token.mint_address
                else None
            )
            if paid_token and paid_token.mint_address:
                logger.info(
                    "Wallet id=%s SPL balance=%s token_symbol=%s mint=%s",
                    wallet.id,
                    balance_spl,
                    getattr(paid_token, "symbol", None),
                    paid_token.mint_address,
                )
            else:
                logger.info("Wallet id=%s has no SPL token/mint configured", wallet.id)

            if balance_sol > 0:
                transaction_type = TransactionTypeEnum.NATIVE
                transaction_amount = balance_sol
                logger.info(
                    "Wallet id=%s selected transfer type=%s amount=%s",
                    wallet.id,
                    transaction_type.value,
                    transaction_amount,
                )
            elif balance_spl and balance_spl > 0:
                transaction_type = TransactionTypeEnum.SPL
                transaction_amount = balance_spl
                logger.info(
                    "Wallet id=%s selected transfer type=%s amount=%s token_symbol=%s mint=%s",
                    wallet.id,
                    transaction_type.value,
                    transaction_amount,
                    getattr(paid_token, "symbol", None),
                    paid_token.mint_address if paid_token else None,
                )
            else:
                OneTimePaymentWallet.objects.filter(id=wallet.id).update(
                    state=OneTimeWalletStateTypes.PAYMENT_EXPIRED,
                    receiver_address=recipient_address,
                )
                logger.info(
                    f"One time wallet with id: {wallet.id} does not have any balance, mark it as payment expired"
                )
                one_time_wallet_service.close_expired_one_time_wallets(
                    sleep_interval_seconds=0.2
                )
                OneTimePaymentWallet.objects.filter(id=wallet.id).update(
                    state=OneTimeWalletStateTypes.PAYMENT_EXPIRED_AND_WALLET_CLOSED
                )
                continue

            logger.info(
                "Sending funds from wallet id=%s type=%s amount=%s to recipient=%s",
                wallet.id,
                transaction_type.value,
                transaction_amount,
                recipient_address,
            )
            send_transaction_and_update_one_time_wallet(
                one_time_wallet=wallet,
                recipient_address=recipient_address,
                amount=transaction_amount,
                transaction_type=TransactionTypeEnum(transaction_type),
                token_mint_address=paid_token.mint_address if paid_token else None,
            )

    def create_payment_crypto_prices_from_allowed_payment_crypto_tokens(self):
        created_crypto_prices = []

        payment_tokens = AllowedPaymentCryptoToken.objects.filter(is_active=True)

        if not payment_tokens.exists():
            raise PaymentConfigurationError(
                "No active payment tokens found. Please configure at least one active payment token "
                "in AllowedPaymentCryptoToken before creating a payment."
            )

        for token in payment_tokens:
            payment_price = token.payment_crypto_price

            payment_price_obj = SolanaPayPaymentCryptoPrice(
                token=token,
                amount_in_crypto=payment_price,
            )
            created_crypto_prices.append(payment_price_obj)

        if not created_crypto_prices:
            raise PaymentConfigurationError(
                "Failed to create payment crypto prices. No prices were generated from active payment tokens."
            )

        logger.info(f"SolanaPay: Created crypto prices: {payment_tokens}")
        SolanaPayPaymentCryptoPrice.objects.bulk_create(created_crypto_prices)
        return created_crypto_prices

    @transaction.atomic
    def create_payment(self, payment_data: dict) -> SolanaPayment:
        """
        Create a new initiated payment with a dedicated one-time wallet and token prices.

        This method is wrapped in a DB transaction to keep payment creation consistent:
        wallet creation record, payment row, and related crypto price links are persisted
        together or rolled back together on failure.

        Flow:
        1. Create one-time wallet (and optional ATAs depending on active SPL tokens).
        2. Create payment in ``INITIATED`` status and bind wallet/address.
        3. Build ``SolanaPayPaymentCryptoPrice`` records from active payment tokens.
        4. Attach created price rows to the payment via M2M.

        Args:
            payment_data: Validated payment payload used to create ``SolanaPayment``.
                Common fields include ``user``, ``label``, ``message``, and ``meta_data``.

        Returns:
            Created ``SolanaPayment`` instance in ``INITIATED`` state.

        Raises:
            PaymentConfigurationError: If there are no active payment tokens or no
                payment prices can be generated from configured tokens.
            Exception: Propagates wallet/payment persistence errors; transaction is rolled back.
        """
        reference_keypair, payment_address, wallet = (
            one_time_wallet_service.create_one_time_wallet()
        )

        payment = SolanaPayment.objects.create(
            **payment_data,
            one_time_payment_wallet=wallet,
            payment_address=payment_address,
            status=SolanaPaymentStatusTypes.INITIATED,
        )

        payment_prices = (
            self.create_payment_crypto_prices_from_allowed_payment_crypto_tokens()
        )

        payment.crypto_prices.add(*payment_prices)

        return payment
