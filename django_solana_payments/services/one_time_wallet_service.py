import logging
import time

from solders.solders import Keypair, Pubkey

from django_solana_payments.choices import OneTimeWalletStateTypes, TokenTypes
from django_solana_payments.helpers import (
    get_payment_crypto_token_model,
    get_solana_payment_model,
)
from django_solana_payments.models import OneTimePaymentWallet
from django_solana_payments.services.wallet_encryption_service import (
    WalletEncryptionService,
)
from django_solana_payments.settings import solana_payments_settings
from django_solana_payments.solana.base_solana_client import base_solana_client
from django_solana_payments.solana.solana_token_client import SolanaTokenClient
from django_solana_payments.utils import chunked

solana_logger = logging.getLogger(__name__)

AllowedPaymentCryptoToken = get_payment_crypto_token_model()


class OneTimeWalletService:
    def __init__(self):
        self.solana_token_client = SolanaTokenClient(
            base_solana_client=base_solana_client
        )
        self.encryption_enabled = (
            solana_payments_settings.ONE_TIME_WALLETS_ENCRYPTION_ENABLED
        )
        self._encryption_service: WalletEncryptionService | None = None

        if self.encryption_enabled:
            key = solana_payments_settings.ONE_TIME_WALLETS_ENCRYPTION_KEY
            self._encryption_service = WalletEncryptionService(key)

    @property
    def _solana_payment_related_name(self):
        SolanaPayment = get_solana_payment_model()
        # Access the reverse relation from SolanaPayPaymentCryptoPrice back to the SolanaPayment model
        return SolanaPayment.crypto_prices.field.remote_field.related_name % {
            "app_label": SolanaPayment._meta.app_label,
            "class": SolanaPayment._meta.model_name,
        }

    def generate_one_time_wallet_and_encrypt_if_needed(self) -> tuple[Keypair, str]:
        """
        Generates one-time wallet on-chain and encrypts if ONE_TIME_WALLETS_ENCRYPTION_ENABLED=True
        """
        keypair = base_solana_client.generate_keypair()

        keypair_json = keypair.to_json()

        if self.encryption_enabled:
            keypair_json = self._encryption_service.encrypt(keypair_json)

        return keypair, keypair_json

    def create_one_time_wallet(
        self, should_create_atas: bool = True
    ) -> tuple[Keypair, str, OneTimePaymentWallet]:
        """
        Creates a record for one time wallet and associated token addresses if needed
        """
        reference_keypair, keypair_json = (
            self.generate_one_time_wallet_and_encrypt_if_needed()
        )
        reference_pubkey_string = str(reference_keypair.pubkey())

        wallet = OneTimePaymentWallet.objects.create(keypair_json=keypair_json)

        solana_logger.info(f"Generated one time wallet: {reference_pubkey_string}")

        if should_create_atas:
            self.create_atas_for_one_time_wallet_from_active_tokens(wallet)
            solana_logger.info(
                f"Generated ATA's for active tokens for one time wallet: {reference_pubkey_string}"
            )

        return reference_keypair, reference_pubkey_string, wallet

    def create_atas_for_one_time_wallet_from_active_tokens(
        self, wallet: OneTimePaymentWallet, max_atas_per_tx: int = 8
    ):

        allowed_payment_crypto_tokens = AllowedPaymentCryptoToken.objects.filter(
            is_active=True, token_type=TokenTypes.SPL
        )

        spl_mints = allowed_payment_crypto_tokens.values_list("mint_address", flat=True)
        spl_mints = [Pubkey.from_string(spl_mint) for spl_mint in spl_mints]

        reference_keypair = self.load_keypair(wallet.keypair_json)

        for chunk in chunked(spl_mints, max_atas_per_tx):
            SolanaTokenClient(
                base_solana_client=base_solana_client
            ).create_associated_token_addresses_for_mints(
                recipient=reference_keypair.pubkey(), mints=chunk
            )

    def load_keypair(self, stored_value: str) -> Keypair:
        if self.encryption_enabled:
            stored_value = self._encryption_service.decrypt(stored_value)

        return Keypair.from_json(stored_value)

    def close_one_time_wallet_atas(
        self,
        one_time_wallet: OneTimePaymentWallet,
        rent_receiver_address: Pubkey,
        max_atas_per_tx: int = 8,
    ) -> bool:
        """
        Closes all empty associated token accounts (ATAs) for a one-time wallet
        and recovers rent to recipient_address.
        """

        decrypted_sender_keypair = self.load_keypair(one_time_wallet.keypair_json)

        solana_logger.info(
            "Closing ATAs for one-time wallet %s (pubkey=%s)",
            one_time_wallet.id,
            decrypted_sender_keypair.pubkey(),
        )

        # 1. Get all mint addresses involved in this payment
        filter_path = f"crypto_prices__{self._solana_payment_related_name}__one_time_payment_wallet"
        mint_addresses = (
            AllowedPaymentCryptoToken.objects.filter(
                **{filter_path: one_time_wallet}, mint_address__isnull=False
            )
            .values_list("mint_address", flat=True)
            .distinct()
        )

        if not mint_addresses:
            solana_logger.info(
                "No associated tokens found for wallet %s", one_time_wallet.id
            )
            return True

        atas_to_close: list[Pubkey] = []
        ata_program_id: Pubkey | None = None

        # 2. Resolve ATAs and validate balances
        for mint_address in mint_addresses:
            mint_pubkey = Pubkey.from_string(mint_address)

            ata = self.solana_token_client.get_associated_token_address(
                decrypted_sender_keypair.pubkey(),
                mint_pubkey,
            )

            ata_info = base_solana_client.http_client.get_account_info(ata).value
            if not ata_info:
                solana_logger.debug("ATA %s does not exist, skipping", ata)
                continue

            ata_program_id = ata_info.owner  # same for all ATAs

            try:
                token_balance = (
                    base_solana_client.http_client.get_token_account_balance(
                        ata
                    ).value.amount
                )
            except Exception as e:
                solana_logger.warning("Failed to read token balance for %s: %s", ata, e)
                continue

            if int(token_balance) > 0:
                solana_logger.info(
                    "ATA %s has non-zero balance (%s); skipping close",
                    ata,
                    token_balance,
                )
                continue

            atas_to_close.append(ata)

        if not atas_to_close:
            solana_logger.info(
                "No ATAs eligible for closing for wallet %s", one_time_wallet.id
            )
            return True

        # 3. Close all eligible ATAs (batch-safe)
        solana_logger.info(
            "Closing %d ATAs for wallet %s",
            len(atas_to_close),
            one_time_wallet.id,
        )

        results = []
        for chunk in chunked(atas_to_close, max_atas_per_tx):
            result = self.solana_token_client.close_associated_token_accounts_and_recover_rent(
                decrypted_sender_keypair,
                accounts_to_close=chunk,
                destination_pubkey=rent_receiver_address,
                ata_program_id=ata_program_id,
            )
            results.append(result)

        return bool(results)

    def close_expired_one_time_wallets(
        self, sleep_interval_seconds: float | int | None = None
    ):
        """
        Close all one-time Solana wallets that are:
        - in PAYMENT_EXPIRED state (linked payment expired).
        """

        target_wallets = OneTimePaymentWallet.objects.filter(
            state__in=[
                OneTimeWalletStateTypes.PAYMENT_EXPIRED,
            ]
        )

        total_wallets = target_wallets.count()
        print(f"Found {total_wallets} one-time wallets to close (PAYMENT_EXPIRED).")

        if total_wallets == 0:
            return

        wallets = list(target_wallets)
        closed_wallets_ids = []
        recipient_address_pubkey = Pubkey.from_string(
            solana_payments_settings.SOLANA_SENDER_ADDRESS
        )

        for wallet in wallets:
            try:

                is_closed = self.close_one_time_wallet_atas(
                    wallet, recipient_address_pubkey
                )
                if is_closed:
                    closed_wallets_ids.append(wallet.id)
                    print(f"Closed one-time wallet: {wallet.id}")

                if sleep_interval_seconds:
                    time.sleep(
                        sleep_interval_seconds
                    )  # prevent blockchain rate limiting
            except Exception as e:
                print(f"Failed to close wallet {wallet.id}: {e}")
                continue

        OneTimePaymentWallet.objects.filter(id__in=closed_wallets_ids).update(
            state=OneTimeWalletStateTypes.PAYMENT_EXPIRED_AND_WALLET_CLOSED,
        )

        print(f"Closed {len(closed_wallets_ids)} of {total_wallets} one-time wallets.")


_one_time_wallet_service_instance = None


def get_one_time_wallet_service() -> OneTimeWalletService:
    """
    Get or create a singleton instance of OneTimeWalletService.
    This allows for easier testing and mocking.

    Usage:
        # In production code
        service = get_one_time_wallet_service()
        wallet = service.create_one_time_wallet()

        # In tests - reset before each test
        reset_one_time_wallet_service()
        service = get_one_time_wallet_service()

        # Or mock the factory function
        with patch('module.get_one_time_wallet_service') as mock:
            mock.return_value = YourMockService()
    """
    global _one_time_wallet_service_instance
    if _one_time_wallet_service_instance is None:
        _one_time_wallet_service_instance = OneTimeWalletService()
    return _one_time_wallet_service_instance


def reset_one_time_wallet_service():
    """
    Reset the singleton instance. Useful for testing.
    """
    global _one_time_wallet_service_instance
    _one_time_wallet_service_instance = None


one_time_wallet_service = get_one_time_wallet_service()
