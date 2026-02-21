from datetime import timedelta
from decimal import Decimal
from unittest.mock import MagicMock, Mock, patch

import pytest
from django.utils import timezone
from solders.pubkey import Pubkey
from solders.signature import Signature
from solders.solders import GetTransactionResp, TransactionConfirmationStatus

from django_solana_payments.choices import (
    OneTimeWalletStateTypes,
    SolanaPaymentStatusTypes,
)
from django_solana_payments.exceptions import (
    InvalidPaymentAmountError,
    PaymentExpiredError,
    PaymentNotFoundError,
)
from django_solana_payments.helpers import (
    get_payment_crypto_token_model,
    get_solana_payment_model,
)
from django_solana_payments.models import (
    OneTimePaymentWallet,
)
from django_solana_payments.services.verify_transaction_service import (
    VerifyTransactionService,
)

SolanaPayment = get_solana_payment_model()
PaymentCryptoToken = get_payment_crypto_token_model()


@pytest.fixture
def expired_payment(db, user):
    """Create an expired solana payment with valid Solana address."""
    # Create a separate one-time wallet for expired payment
    expired_wallet = OneTimePaymentWallet.objects.create(
        keypair_json="[1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56,57,58,59,60,61,62,63,64]",
        state=OneTimeWalletStateTypes.CREATED,
    )
    payment = SolanaPayment.objects.create(
        user=user,
        payment_address="TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",  # Valid Solana address (Token program)
        one_time_payment_wallet=expired_wallet,
        status=SolanaPaymentStatusTypes.INITIATED,
        expiration_date=timezone.now() - timedelta(hours=1),
        label="Expired Payment",
        message="Expired payment message",
    )
    return payment


class TestVerifyTransactionAndProcessPayment:

    @pytest.mark.django_db
    def test_payment_not_found(self, payment_token):
        """Test that PaymentNotFoundError is raised when payment doesn't exist."""
        service = VerifyTransactionService()

        with pytest.raises(PaymentNotFoundError):
            service.verify_transaction_and_process_payment(
                payment_address="3" * 44,  # Valid but non-existent address
                payment_crypto_token=payment_token,
            )

    @pytest.mark.django_db
    def test_payment_expired(self, expired_payment, payment_token):
        """Test that PaymentExpiredError is raised for expired payments."""
        service = VerifyTransactionService()

        with pytest.raises(PaymentExpiredError):
            service.verify_transaction_and_process_payment(
                payment_address=expired_payment.payment_address,
                payment_crypto_token=payment_token,
            )

        # Verify payment status was updated to EXPIRED
        expired_payment.refresh_from_db()
        assert expired_payment.status == SolanaPaymentStatusTypes.EXPIRED

        # Verify wallet state was updated
        expired_payment.one_time_payment_wallet.refresh_from_db()
        assert (
            expired_payment.one_time_payment_wallet.state
            == OneTimeWalletStateTypes.PAYMENT_EXPIRED
        )

    @pytest.mark.django_db
    def test_payment_already_confirmed(self, solana_payment, payment_token):
        """Test that already confirmed payment returns its status."""
        solana_payment.status = SolanaPaymentStatusTypes.CONFIRMED
        solana_payment.save()

        service = VerifyTransactionService()

        result = service.verify_transaction_and_process_payment(
            payment_address=solana_payment.payment_address,
            payment_crypto_token=payment_token,
        )

        assert result == SolanaPaymentStatusTypes.CONFIRMED

    @pytest.mark.django_db
    def test_payment_already_finalized(self, solana_payment, payment_token):
        """Test that already finalized payment returns its status."""
        solana_payment.status = SolanaPaymentStatusTypes.FINALIZED
        solana_payment.save()

        service = VerifyTransactionService()

        result = service.verify_transaction_and_process_payment(
            payment_address=solana_payment.payment_address,
            payment_crypto_token=payment_token,
        )

        assert result == SolanaPaymentStatusTypes.FINALIZED

    @pytest.mark.django_db
    @patch(
        "django_solana_payments.services.verify_transaction_service.SolanaBalanceClient"
    )
    @patch(
        "django_solana_payments.services.verify_transaction_service.SolanaTransactionQueryClient"
    )
    def test_no_transactions_found(
        self,
        mock_query_client_class,
        mock_balance_client_class,
        solana_payment,
        payment_token,
        payment_crypto_price,
    ):
        """Test when no transactions are found for the payment address."""
        # Setup mocks
        mock_balance_client = MagicMock()
        mock_balance_client.get_balance_by_address.return_value = Decimal("0.1")
        mock_balance_client_class.return_value = mock_balance_client

        mock_query_client = MagicMock()
        mock_query_client.get_transactions_for_address.return_value = []
        mock_query_client_class.return_value = mock_query_client

        service = VerifyTransactionService()

        result = service.verify_transaction_and_process_payment(
            payment_address=solana_payment.payment_address,
            payment_crypto_token=payment_token,
        )

        assert result == SolanaPaymentStatusTypes.INITIATED

    @pytest.mark.django_db
    @patch(
        "django_solana_payments.services.verify_transaction_service.send_solana_transaction_to_main_wallet"
    )
    @patch(
        "django_solana_payments.services.verify_transaction_service.SolanaBalanceClient"
    )
    @patch(
        "django_solana_payments.services.verify_transaction_service.SolanaTransactionQueryClient"
    )
    def test_successful_payment_verification_native_sol(
        self,
        mock_query_client_class,
        mock_balance_client_class,
        mock_send_to_main,
        solana_payment,
        payment_token,
        payment_crypto_price,
        test_settings,
        settings,
    ):
        """Test successful payment verification for native SOL."""
        # Setup test settings
        settings.SOLANA_PAYMENTS = test_settings

        # Setup balance client mock
        mock_balance_client = MagicMock()
        mock_balance_client.get_balance_by_address.return_value = Decimal("0.1")
        mock_balance_client_class.return_value = mock_balance_client

        # Setup transaction query client mock
        mock_query_client = MagicMock()

        # Create mock transaction
        mock_transaction = MagicMock(spec=GetTransactionResp)
        mock_transaction.value.transaction.transaction.signatures = [
            Signature.from_string("5" * 88)  # Valid signature format
        ]

        # Mock transaction status
        mock_tx_status = MagicMock()
        mock_tx_status.confirmation_status = TransactionConfirmationStatus.Confirmed
        mock_query_client.get_signatures_statuses.return_value = [mock_tx_status]

        mock_query_client.get_transactions_for_address.return_value = [mock_transaction]

        # Mock fee payer to not be sender address
        mock_fee_payer = Pubkey.from_string("2" * 44)
        mock_query_client.extract_fee_payer_from_transaction_details.return_value = (
            mock_fee_payer
        )

        mock_query_client_class.return_value = mock_query_client

        # Add payment to crypto price relationship
        solana_payment.crypto_prices.add(payment_crypto_price)

        service = VerifyTransactionService()

        result = service.verify_transaction_and_process_payment(
            payment_address=solana_payment.payment_address,
            payment_crypto_token=payment_token,
        )

        # Verify result
        assert result in [
            SolanaPaymentStatusTypes.CONFIRMED,
            SolanaPaymentStatusTypes.FINALIZED,
        ]

        # Verify payment was updated
        solana_payment.refresh_from_db()
        assert solana_payment.status in [
            SolanaPaymentStatusTypes.CONFIRMED,
            SolanaPaymentStatusTypes.FINALIZED,
        ]
        assert solana_payment.paid_token == payment_token

        # Verify send to main wallet was called
        mock_send_to_main.assert_called_once()

    @pytest.mark.django_db
    @patch(
        "django_solana_payments.services.verify_transaction_service.SolanaBalanceClient"
    )
    @patch(
        "django_solana_payments.services.verify_transaction_service.SolanaTransactionQueryClient"
    )
    def test_invalid_payment_amount(
        self,
        mock_query_client_class,
        mock_balance_client_class,
        solana_payment,
        payment_token,
        payment_crypto_price,
        test_settings,
        settings,
    ):
        """Test that InvalidPaymentAmountError is raised when amount doesn't match."""
        # Setup test settings
        settings.SOLANA_PAYMENTS = test_settings

        # Setup balance client mock - balance less than expected
        mock_balance_client = MagicMock()
        mock_balance_client.get_balance_by_address.return_value = Decimal(
            "0.05"
        )  # Less than expected 0.1
        mock_balance_client_class.return_value = mock_balance_client

        # Setup transaction query client mock
        mock_query_client = MagicMock()

        # Create mock transaction
        mock_transaction = MagicMock(spec=GetTransactionResp)
        mock_query_client.get_transactions_for_address.return_value = [mock_transaction]

        # Mock fee payer to not be sender address
        mock_fee_payer = Pubkey.from_string("2" * 44)
        mock_query_client.extract_fee_payer_from_transaction_details.return_value = (
            mock_fee_payer
        )

        mock_query_client_class.return_value = mock_query_client

        # Add payment to crypto price relationship
        solana_payment.crypto_prices.add(payment_crypto_price)

        service = VerifyTransactionService()

        with pytest.raises(InvalidPaymentAmountError):
            service.verify_transaction_and_process_payment(
                payment_address=solana_payment.payment_address,
                payment_crypto_token=payment_token,
            )

    @pytest.mark.django_db
    def test_wallet_state_updated_to_processing(self, solana_payment, payment_token):
        """Test that wallet state is updated to PROCESSING_PAYMENT."""
        service = VerifyTransactionService()

        # Mock to prevent actual transaction verification
        with patch.object(
            service,
            "validate_solana_payment",
            return_value=SolanaPaymentStatusTypes.CONFIRMED,
        ):
            service.verify_transaction_and_process_payment(
                payment_address=solana_payment.payment_address,
                payment_crypto_token=payment_token,
            )

        # Verify wallet state
        solana_payment.one_time_payment_wallet.refresh_from_db()
        assert (
            solana_payment.one_time_payment_wallet.state
            == OneTimeWalletStateTypes.PROCESSING_PAYMENT
        )

    @pytest.mark.django_db
    @patch(
        "django_solana_payments.services.verify_transaction_service.solana_payment_accepted"
    )
    @patch(
        "django_solana_payments.services.verify_transaction_service.send_solana_transaction_to_main_wallet"
    )
    @patch(
        "django_solana_payments.services.verify_transaction_service.SolanaBalanceClient"
    )
    @patch(
        "django_solana_payments.services.verify_transaction_service.SolanaTransactionQueryClient"
    )
    def test_signal_sent_on_success(
        self,
        mock_query_client_class,
        mock_balance_client_class,
        mock_send_to_main,
        mock_signal,
        solana_payment,
        payment_token,
        payment_crypto_price,
        test_settings,
        settings,
    ):
        """Test that solana_payment_accepted signal is sent on successful payment."""
        # Setup test settings
        settings.SOLANA_PAYMENTS = test_settings

        # Setup mocks
        mock_balance_client = MagicMock()
        mock_balance_client.get_balance_by_address.return_value = Decimal("0.1")
        mock_balance_client_class.return_value = mock_balance_client

        mock_query_client = MagicMock()
        mock_transaction = MagicMock(spec=GetTransactionResp)
        mock_transaction.value.transaction.transaction.signatures = [
            Signature.from_string("5" * 88)
        ]

        mock_tx_status = MagicMock()
        mock_tx_status.confirmation_status = TransactionConfirmationStatus.Confirmed
        mock_query_client.get_signatures_statuses.return_value = [mock_tx_status]
        mock_query_client.get_transactions_for_address.return_value = [mock_transaction]
        mock_query_client.extract_fee_payer_from_transaction_details.return_value = (
            Pubkey.from_string("2" * 44)
        )
        mock_query_client_class.return_value = mock_query_client
        mock_signal.send_robust.return_value = []

        solana_payment.crypto_prices.add(payment_crypto_price)

        service = VerifyTransactionService()
        with patch(
            "django_solana_payments.services.verify_transaction_service.transaction.on_commit",
            side_effect=lambda fn: fn(),
        ):
            service.verify_transaction_and_process_payment(
                payment_address=solana_payment.payment_address,
                payment_crypto_token=payment_token,
                send_payment_accepted_signal=True,
            )

        # Verify signal was sent with robust dispatch
        mock_signal.send_robust.assert_called_once()
        call_kwargs = mock_signal.send_robust.call_args[1]
        assert call_kwargs["payment"] == solana_payment
        assert call_kwargs["transaction_status"] in [
            SolanaPaymentStatusTypes.CONFIRMED,
            SolanaPaymentStatusTypes.FINALIZED,
        ]

    @pytest.mark.django_db
    @patch(
        "django_solana_payments.services.verify_transaction_service.solana_payment_accepted"
    )
    @patch(
        "django_solana_payments.services.verify_transaction_service.send_solana_transaction_to_main_wallet"
    )
    @patch(
        "django_solana_payments.services.verify_transaction_service.SolanaBalanceClient"
    )
    @patch(
        "django_solana_payments.services.verify_transaction_service.SolanaTransactionQueryClient"
    )
    def test_signal_failure_does_not_break_payment_processing(
        self,
        mock_query_client_class,
        mock_balance_client_class,
        _mock_send_to_main,
        mock_signal,
        solana_payment,
        payment_token,
        payment_crypto_price,
        test_settings,
        settings,
    ):
        settings.SOLANA_PAYMENTS = test_settings

        mock_balance_client = MagicMock()
        mock_balance_client.get_balance_by_address.return_value = Decimal("0.1")
        mock_balance_client_class.return_value = mock_balance_client

        mock_query_client = MagicMock()
        mock_transaction = MagicMock(spec=GetTransactionResp)
        mock_transaction.value.transaction.transaction.signatures = [
            Signature.from_string("5" * 88)
        ]
        mock_tx_status = MagicMock()
        mock_tx_status.confirmation_status = TransactionConfirmationStatus.Confirmed
        mock_query_client.get_signatures_statuses.return_value = [mock_tx_status]
        mock_query_client.get_transactions_for_address.return_value = [mock_transaction]
        mock_query_client.extract_fee_payer_from_transaction_details.return_value = (
            Pubkey.from_string("2" * 44)
        )
        mock_query_client_class.return_value = mock_query_client

        mock_signal.send_robust.return_value = [
            (object(), RuntimeError("receiver failed"))
        ]
        solana_payment.crypto_prices.add(payment_crypto_price)

        service = VerifyTransactionService()
        with patch(
            "django_solana_payments.services.verify_transaction_service.transaction.on_commit",
            side_effect=lambda fn: fn(),
        ):
            service.verify_transaction_and_process_payment(
                payment_address=solana_payment.payment_address,
                payment_crypto_token=payment_token,
                send_payment_accepted_signal=True,
            )

        mock_signal.send_robust.assert_called_once()

    @pytest.mark.django_db
    @patch(
        "django_solana_payments.services.verify_transaction_service.solana_payment_accepted"
    )
    @patch(
        "django_solana_payments.services.verify_transaction_service.send_solana_transaction_to_main_wallet"
    )
    @patch(
        "django_solana_payments.services.verify_transaction_service.SolanaBalanceClient"
    )
    @patch(
        "django_solana_payments.services.verify_transaction_service.SolanaTransactionQueryClient"
    )
    def test_on_success_callback_called(
        self,
        mock_query_client_class,
        mock_balance_client_class,
        mock_send_to_main,
        mock_signal,
        solana_payment,
        payment_token,
        payment_crypto_price,
        test_settings,
        settings,
    ):
        """Test that on_success callback is called on successful payment."""
        # Setup test settings
        settings.SOLANA_PAYMENTS = test_settings

        # Setup mocks
        mock_balance_client = MagicMock()
        mock_balance_client.get_balance_by_address.return_value = Decimal("0.1")
        mock_balance_client_class.return_value = mock_balance_client

        mock_query_client = MagicMock()
        mock_transaction = MagicMock(spec=GetTransactionResp)
        mock_transaction.value.transaction.transaction.signatures = [
            Signature.from_string("5" * 88)
        ]

        mock_tx_status = MagicMock()
        mock_tx_status.confirmation_status = TransactionConfirmationStatus.Confirmed
        mock_query_client.get_signatures_statuses.return_value = [mock_tx_status]
        mock_query_client.get_transactions_for_address.return_value = [mock_transaction]
        mock_query_client.extract_fee_payer_from_transaction_details.return_value = (
            Pubkey.from_string("2" * 44)
        )
        mock_query_client_class.return_value = mock_query_client
        mock_signal.send_robust.return_value = []

        solana_payment.crypto_prices.add(payment_crypto_price)

        # Create mock callback
        mock_callback = Mock()

        service = VerifyTransactionService()
        with patch(
            "django_solana_payments.services.verify_transaction_service.transaction.on_commit",
            side_effect=lambda fn: fn(),
        ):
            service.verify_transaction_and_process_payment(
                payment_address=solana_payment.payment_address,
                payment_crypto_token=payment_token,
                on_success=mock_callback,
            )

        # Verify callback was called
        mock_callback.assert_called_once()
        args = mock_callback.call_args[0]
        assert args[0] == solana_payment
        assert args[1] in [
            SolanaPaymentStatusTypes.CONFIRMED,
            SolanaPaymentStatusTypes.FINALIZED,
        ]

    @pytest.mark.django_db
    @patch(
        "django_solana_payments.services.verify_transaction_service.send_solana_transaction_to_main_wallet"
    )
    @patch(
        "django_solana_payments.services.verify_transaction_service.SolanaBalanceClient"
    )
    @patch(
        "django_solana_payments.services.verify_transaction_service.SolanaTransactionQueryClient"
    )
    def test_metadata_saved_with_payment(
        self,
        mock_query_client_class,
        mock_balance_client_class,
        mock_send_to_main,
        solana_payment,
        payment_token,
        payment_crypto_price,
        test_settings,
        settings,
    ):
        """Test that metadata is saved with the payment."""
        # Setup test settings
        settings.SOLANA_PAYMENTS = test_settings

        # Setup mocks
        mock_balance_client = MagicMock()
        mock_balance_client.get_balance_by_address.return_value = Decimal("0.1")
        mock_balance_client_class.return_value = mock_balance_client

        mock_query_client = MagicMock()
        mock_transaction = MagicMock(spec=GetTransactionResp)
        mock_transaction.value.transaction.transaction.signatures = [
            Signature.from_string("5" * 88)
        ]

        mock_tx_status = MagicMock()
        mock_tx_status.confirmation_status = TransactionConfirmationStatus.Confirmed
        mock_query_client.get_signatures_statuses.return_value = [mock_tx_status]
        mock_query_client.get_transactions_for_address.return_value = [mock_transaction]
        mock_query_client.extract_fee_payer_from_transaction_details.return_value = (
            Pubkey.from_string("2" * 44)
        )
        mock_query_client_class.return_value = mock_query_client

        solana_payment.crypto_prices.add(payment_crypto_price)

        # Custom metadata
        test_metadata = {"order_id": "12345", "customer_email": "test@example.com"}

        service = VerifyTransactionService()
        service.verify_transaction_and_process_payment(
            payment_address=solana_payment.payment_address,
            payment_crypto_token=payment_token,
            meta_data=test_metadata,
            send_payment_accepted_signal=False,
        )

        # Verify metadata was saved
        solana_payment.refresh_from_db()
        assert solana_payment.meta_data == test_metadata

    @pytest.mark.django_db
    @patch(
        "django_solana_payments.services.verify_transaction_service.solana_payment_accepted"
    )
    @patch(
        "django_solana_payments.services.verify_transaction_service.send_solana_transaction_to_main_wallet"
    )
    @patch(
        "django_solana_payments.services.verify_transaction_service.SolanaBalanceClient"
    )
    @patch(
        "django_solana_payments.services.verify_transaction_service.SolanaTransactionQueryClient"
    )
    def test_existing_metadata_is_preserved_when_meta_data_not_passed(
        self,
        mock_query_client_class,
        mock_balance_client_class,
        _mock_send_to_main,
        mock_signal,
        solana_payment,
        payment_token,
        payment_crypto_price,
        test_settings,
        settings,
    ):
        settings.SOLANA_PAYMENTS = test_settings

        solana_payment.meta_data = {"simulate_hook_failures": ["analytics"]}
        solana_payment.save(update_fields=["meta_data", "updated"])

        mock_balance_client = MagicMock()
        mock_balance_client.get_balance_by_address.return_value = Decimal("0.1")
        mock_balance_client_class.return_value = mock_balance_client

        mock_query_client = MagicMock()
        mock_transaction = MagicMock(spec=GetTransactionResp)
        mock_transaction.value.transaction.transaction.signatures = [
            Signature.from_string("5" * 88)
        ]
        mock_tx_status = MagicMock()
        mock_tx_status.confirmation_status = TransactionConfirmationStatus.Confirmed
        mock_query_client.get_signatures_statuses.return_value = [mock_tx_status]
        mock_query_client.get_transactions_for_address.return_value = [mock_transaction]
        mock_query_client.extract_fee_payer_from_transaction_details.return_value = (
            Pubkey.from_string("2" * 44)
        )
        mock_query_client_class.return_value = mock_query_client
        mock_signal.send_robust.return_value = []
        solana_payment.crypto_prices.add(payment_crypto_price)

        with patch(
            "django_solana_payments.services.verify_transaction_service.transaction.on_commit",
            side_effect=lambda fn: fn(),
        ):
            VerifyTransactionService().verify_transaction_and_process_payment(
                payment_address=solana_payment.payment_address,
                payment_crypto_token=payment_token,
                send_payment_accepted_signal=True,
            )

        solana_payment.refresh_from_db()
        assert solana_payment.meta_data["simulate_hook_failures"] == ["analytics"]
