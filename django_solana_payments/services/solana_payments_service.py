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
from django_solana_payments.exceptions import PaymentConfigurationError
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
from django_solana_payments.settings import solana_payments_settings
from django_solana_payments.solana.base_solana_client import base_solana_client
from django_solana_payments.solana.enums import TransactionTypeEnum
from django_solana_payments.solana.solana_balance_client import SolanaBalanceClient

logger = logging.getLogger(__name__)

AllowedPaymentCryptoToken = get_payment_crypto_token_model()
SolanaPayment = get_solana_payment_model()


class SolanaPaymentsService:

    def check_expired_solana_payments(self):
        expired_payments = SolanaPayment.objects.filter(
            status=SolanaPaymentStatusTypes.INITIATED,
            expiration_date__lte=timezone.now(),
        )
        total_not_finished_payments = expired_payments.count()
        print(f"Total not finished solana payments: {total_not_finished_payments}")

        if total_not_finished_payments == 0:
            return

        expired_payments.update(status=SolanaPaymentStatusTypes.EXPIRED)

        wallet_ids = expired_payments.filter(
            one_time_payment_wallet__isnull=False
        ).values_list("one_time_payment_wallet__id", flat=True)

        OneTimePaymentWallet.objects.filter(id__in=list(wallet_ids)).update(
            state=OneTimeWalletStateTypes.PAYMENT_EXPIRED
        )

        print(
            f"Marked {total_not_finished_payments} expired payments and their wallets."
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
        print(f"Found {count} one-time wallets to process.")

        if count == 0:
            return

        solana_balance_client = SolanaBalanceClient(
            base_solana_client=base_solana_client
        )

        for wallet in one_time_wallets_with_balance:
            wallet_keypair = one_time_wallet_service.load_keypair(wallet.keypair_json)
            wallet_address = wallet_keypair.pubkey()
            recipient_address = solana_payments_settings.RECEIVER_ADDRESS

            if sleep_interval_seconds:
                time.sleep(sleep_interval_seconds)  # To prevent rate limiting
            balance_sol = solana_balance_client.get_balance_by_address(wallet_address)

            payment = getattr(wallet, payment_wallet_related_name)
            paid_token = payment.paid_token

            balance_spl = (
                solana_balance_client.get_spl_token_balance_by_address(
                    wallet_address, Pubkey.from_string(paid_token.mint_address)
                )
                if paid_token and paid_token.mint_address
                else None
            )

            if balance_sol > 0:
                transaction_type = TransactionTypeEnum.NATIVE
                transaction_amount = balance_sol
            elif balance_spl and balance_spl > 0:
                transaction_type = TransactionTypeEnum.SPL
                transaction_amount = balance_spl
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

            send_transaction_and_update_one_time_wallet(
                one_time_wallet=wallet,
                recipient_address=recipient_address,
                amount=transaction_amount,
                transaction_type=transaction_type,
                update_filters_kwargs={"id": wallet.id},
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
