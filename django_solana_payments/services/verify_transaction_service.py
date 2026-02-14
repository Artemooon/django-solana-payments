import logging
from decimal import Decimal
from typing import Any, Type

from django.utils import timezone
from solana.rpc.commitment import Commitment, Confirmed, Finalized, Processed
from solders.pubkey import Pubkey
from solders.signature import Signature
from solders.solders import GetTransactionResp, TransactionConfirmationStatus

from django_solana_payments.choices import (
    OneTimeWalletStateTypes,
    SolanaPaymentStatusTypes,
    TokenTypes,
)
from django_solana_payments.exceptions import (
    InvalidPaymentAmountError,
    PaymentExpiredError,
    PaymentNotConfirmedError,
    PaymentNotFoundError,
    PaymentTokenPriceNotFoundError,
)
from django_solana_payments.helpers import (
    get_solana_payment_model,
    get_solana_payment_related_name,
)
from django_solana_payments.models import (
    AbstractPaymentToken,
    OneTimePaymentWallet,
    SolanaPayPaymentCryptoPrice,
)
from django_solana_payments.services.main_wallet_service import (
    send_solana_transaction_to_main_wallet,
)
from django_solana_payments.settings import solana_payments_settings
from django_solana_payments.signals import solana_payment_accepted
from django_solana_payments.solana.base_solana_client import base_solana_client
from django_solana_payments.solana.enums import TransactionTypeEnum
from django_solana_payments.solana.solana_balance_client import SolanaBalanceClient
from django_solana_payments.solana.solana_token_client import SolanaTokenClient
from django_solana_payments.solana.solana_transaction_query_client import (
    SolanaTransactionQueryClient,
)

logger = logging.getLogger(__name__)

SolanaPayment = get_solana_payment_model()


class VerifyTransactionService:
    def __init__(self):
        self.solana_balance_client = SolanaBalanceClient(
            base_solana_client=base_solana_client
        )
        self.solana_token_client = SolanaTokenClient(
            base_solana_client=base_solana_client
        )
        self.solana_transaction_query_client = SolanaTransactionQueryClient(
            base_solana_client=base_solana_client
        )

    def verify_transaction_and_process_payment(
        self,
        payment_address: str,
        payment_crypto_token: Type[AbstractPaymentToken],
        meta_data: dict[str, Any] = None,
        send_payment_accepted_signal: bool = True,
        on_success: callable = None,
    ) -> SolanaPaymentStatusTypes:
        logger.info(
            f"Starting verification for payment_address={payment_address}, and token: {payment_crypto_token.mint_address}"
        )

        solana_payment = (
            SolanaPayment.objects.select_related("one_time_payment_wallet")
            .filter(payment_address=payment_address)
            .first()
        )

        if not solana_payment:
            raise PaymentNotFoundError(payment_address)

        OneTimePaymentWallet.objects.filter(
            id=solana_payment.one_time_payment_wallet.id
        ).update(state=OneTimeWalletStateTypes.PROCESSING_PAYMENT)
        receiver_address = Pubkey.from_string(payment_address)

        status = self.validate_solana_payment(solana_payment)

        if status:
            return status

        recipient_wallet_transactions, payment_balance = self.validate_transfer_amount(
            solana_payment,
            receiver_address,
            payment_crypto_token,
            payment_crypto_token.token_type,
        )
        logger.info(
            f"Found {len(recipient_wallet_transactions)} recipient transactions, balance={payment_balance}"
        )

        if recipient_wallet_transactions:
            paid_transaction = recipient_wallet_transactions[0]

            transaction_status = self.accept_verified_transaction_and_process_payment(
                paid_transaction,
                payment_balance,
                payment_crypto_token,
                solana_payment,
                meta_data,
            )

            if send_payment_accepted_signal:
                solana_payment_accepted.send(
                    sender=self.__class__,
                    payment=solana_payment,
                    transaction_status=transaction_status,
                    payment_amount=payment_balance,
                )

            if on_success:
                on_success(solana_payment, transaction_status)

            return transaction_status

        else:
            logger.warning(
                f"No recipient transactions found for payment_address={payment_address}"
            )
            return SolanaPaymentStatusTypes.INITIATED

    def _is_transaction_confirmed(self, transaction: GetTransactionResp) -> bool:
        """
        Checks if a transaction has reached the desired commitment level provided in PAYMENT_ACCEPTANCE_COMMITMENT setting.
        """
        user_commitment = solana_payments_settings.PAYMENT_ACCEPTANCE_COMMITMENT
        transaction_sig = transaction.value.transaction.transaction.signatures[0]
        transaction_statuses = (
            self.solana_transaction_query_client.get_signatures_statuses(
                [transaction_sig]
            )
        )
        confirmation_status = transaction_statuses[0].confirmation_status

        # Map commitment level to required confirmation status
        if user_commitment == Finalized:
            return confirmation_status == TransactionConfirmationStatus.Finalized
        elif user_commitment == Confirmed:
            return confirmation_status in (
                TransactionConfirmationStatus.Confirmed,
                TransactionConfirmationStatus.Finalized,
            )
        elif user_commitment == Processed:
            return confirmation_status in (
                TransactionConfirmationStatus.Processed,
                TransactionConfirmationStatus.Confirmed,
                TransactionConfirmationStatus.Finalized,
            )
        return False

    def accept_verified_transaction_and_process_payment(
        self,
        paid_transaction: GetTransactionResp,
        payment_balance: Decimal,
        payment_crypto_token: Type[AbstractPaymentToken],
        solana_payment: SolanaPayment,
        meta_data: dict[str, Any] = None,
        send_funds_to_main_wallet_immediately: bool = True,
    ):
        if not self._is_transaction_confirmed(paid_transaction):
            raise PaymentNotConfirmedError()

        paid_transaction_signatures = (
            paid_transaction.value.transaction.transaction.signatures
        )

        paid_transaction_signature = paid_transaction_signatures[
            len(paid_transaction_signatures) - 1
        ]

        transaction_status = self.commitment_to_payment_status(
            solana_payments_settings.PAYMENT_ACCEPTANCE_COMMITMENT
        )

        self.update_solana_payment(
            solana_payment,
            transaction_status,
            paid_transaction_signature,
            payment_crypto_token,
            meta_data,
        )

        if send_funds_to_main_wallet_immediately:
            send_solana_transaction_to_main_wallet(
                solana_payments_settings.SOLANA_RECEIVER_ADDRESS,
                solana_payment.one_time_payment_wallet,
                payment_balance,
                (
                    TransactionTypeEnum.SPL.value
                    if payment_crypto_token.token_type == TokenTypes.SPL
                    else TransactionTypeEnum.NATIVE.value
                ),
                payment_crypto_token.mint_address,
            )

        return transaction_status

    @staticmethod
    def commitment_to_payment_status(
        commitment: Commitment,
    ) -> SolanaPaymentStatusTypes:
        """
        Maps a Commitment level to its corresponding SolanaPaymentStatusTypes.
        """
        if commitment == Finalized:
            return SolanaPaymentStatusTypes.FINALIZED
        elif commitment == Confirmed:
            return SolanaPaymentStatusTypes.CONFIRMED
        elif commitment == Processed:
            return SolanaPaymentStatusTypes.PROCESSED
        return SolanaPaymentStatusTypes.INITIATED

    def validate_solana_payment(
        self, solana_payment: SolanaPayment
    ) -> SolanaPaymentStatusTypes | None:
        if not solana_payment:
            raise PaymentNotFoundError(solana_payment.payment_address)

        if solana_payment.status in [
            SolanaPaymentStatusTypes.CONFIRMED,
            SolanaPaymentStatusTypes.FINALIZED,
        ]:
            logger.info(
                f"Payment already confirmed/finalized: status={solana_payment.status}"
            )
            return solana_payment.status

        if timezone.now() > solana_payment.expiration_date:
            SolanaPayment.objects.filter(id=solana_payment.id).update(
                status=SolanaPaymentStatusTypes.EXPIRED
            )
            OneTimePaymentWallet.objects.filter(
                id=solana_payment.one_time_payment_wallet.id
            ).update(state=OneTimeWalletStateTypes.PAYMENT_EXPIRED)
            logger.warning(
                f"Payment expired: payment_address={solana_payment.payment_address}"
            )
            raise PaymentExpiredError()

        return None

    def validate_transfer_amount(
        self,
        solana_payment: SolanaPayment,
        receiver_address: Pubkey,
        payment_crypto_token: Type[AbstractPaymentToken],
        token_type: TokenTypes,
    ) -> tuple[list[GetTransactionResp], Decimal]:
        """
        Validates that the transfer amount is correct based on the payment type.

        For SPL token payments, it checks the spl token balance on the associated token account.
        For SOL payments, it checks the native SOL balance.

        If there are previous transactions (excluding those sent by the configured sender)
        and the expected payment amount exceeds the current balance, a InvalidPaymentAmountError is raised.
        """
        if token_type == TokenTypes.SPL:
            balance = self.solana_balance_client.get_spl_token_balance_by_address(
                receiver_address, Pubkey.from_string(payment_crypto_token.mint_address)
            )
            logger.info(f"SPL token balance for {receiver_address} = {balance}")
            target_address = (
                self.solana_token_client.get_or_create_associated_token_address(
                    receiver_address,
                    Pubkey.from_string(payment_crypto_token.mint_address),
                )
            )
        else:
            balance = self.solana_balance_client.get_balance_by_address(
                receiver_address
            )
            logger.info(f"Native SOL balance for {receiver_address} = {balance}")
            target_address = receiver_address

        crypto_prices_related_name = get_solana_payment_related_name("crypto_prices")
        payment_token_price = SolanaPayPaymentCryptoPrice.objects.filter(
            **{f"{crypto_prices_related_name}__in": [solana_payment]},
            token=payment_crypto_token,
        ).first()

        if not payment_token_price:
            raise PaymentTokenPriceNotFoundError(payment_crypto_token.mint_address)

        expected_amount = payment_token_price.amount_in_crypto

        all_transactions = (
            self.solana_transaction_query_client.get_transactions_for_address(
                address=target_address
            )
        )
        # Exclude transactions sent by the configured sender
        recipient_wallet_transactions: list[GetTransactionResp] = []
        for tx in all_transactions:
            fee_payer = self.solana_transaction_query_client.extract_fee_payer_from_transaction_details(
                tx
            )
            if fee_payer:
                if fee_payer == Pubkey.from_string(
                    solana_payments_settings.SOLANA_FEE_PAYER_ADDRESS
                ):
                    logger.warning(
                        f"Ignoring transaction {tx.value.transaction.transaction.signatures} because fee payer is SOLANA_FEE_PAYER_ADDRESS"
                    )
                else:
                    recipient_wallet_transactions.append(tx)

        if recipient_wallet_transactions and expected_amount > balance:
            logger.error(
                f"Invalid transfer amount: expected={expected_amount}, actual={balance}"
            )
            raise InvalidPaymentAmountError(
                expected=expected_amount,
                actual=balance,
            )

        return recipient_wallet_transactions, balance

    def update_solana_payment(
        self,
        solana_payment: SolanaPayment,
        transaction_status: SolanaPaymentStatusTypes,
        signature: Signature,
        paid_token: Type[AbstractPaymentToken],
        meta_data: dict[str, Any] = None,
    ):
        logger.info(
            "Processing payment transaction for payment_id=%s, status=%s",
            solana_payment.id,
            transaction_status,
        )

        SolanaPayment.objects.filter(id=solana_payment.id).update(
            status=transaction_status,
            signature=signature,
            paid_token=paid_token,
            meta_data=meta_data,
        )

        if transaction_status not in {
            SolanaPaymentStatusTypes.CONFIRMED,
            SolanaPaymentStatusTypes.FINALIZED,
        }:
            raise PaymentNotConfirmedError()

        logger.info(
            "Payment transaction processed and status updated: status=%s",
            transaction_status,
        )
