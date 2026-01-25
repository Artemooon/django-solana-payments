from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.db import models
from django.db.models import CheckConstraint, Q
from django_solana_payments.settings import solana_payments_settings

from django_solana_payments.choices import OneTimeWalletStateTypes, TokenTypes, SolanaPaymentStatusTypes
from django_solana_payments.services.wallet_encryption_service import WalletEncryptionService
from solders.solders import Keypair

from django_solana_payments.utils import set_default_expiration_date

User = get_user_model()


class AbstractPaymentToken(models.Model):
    is_active = models.BooleanField(default=True, db_index=True)

    token_type = models.CharField(
        max_length=15,
        choices=TokenTypes.choices,
        db_index=True,
    )

    mint_address = models.CharField(
        max_length=64,
        unique=True,
        null=True,
        blank=True,
    )

    payment_crypto_price = models.DecimalField(
        max_digits=30,
        decimal_places=18,
    )

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

    @property
    def requires_mint(self) -> bool:
        return self.token_type == TokenTypes.SPL

    def clean(self):
        if self.token_type == TokenTypes.SPL and not self.mint_address:
            raise ValidationError("mint_address is required for SPL tokens")

        if self.token_type == TokenTypes.NATIVE and self.mint_address:
            raise ValidationError("mint_address must be null for native SOL")


class AbstractSolanaPayment(models.Model):
    payment_address = models.CharField(max_length=60)

    one_time_payment_wallet = models.OneToOneField(
        "django_solana_payments.OneTimePaymentWallet",
        on_delete=models.PROTECT,
        related_name="%(app_label)s_%(class)s_payment",
    )

    crypto_prices = models.ManyToManyField(
        "django_solana_payments.SolanaPayPaymentCryptoPrice",
        related_name="%(app_label)s_%(class)s_payments",
    )

    paid_token = models.ForeignKey(
        solana_payments_settings.PAYMENT_CRYPTO_TOKEN_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    status = models.CharField(
        max_length=10,
        choices=SolanaPaymentStatusTypes.choices,
    )

    signature = models.CharField(max_length=255, null=True, blank=True)
    expiration_date = models.DateTimeField(default=set_default_expiration_date)
    meta_data = models.JSONField(default=dict, blank=True, null=True)

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

class PaymentCryptoToken(AbstractPaymentToken):
    name = models.CharField(max_length=255)
    symbol = models.CharField(max_length=128, unique=True)
    meta_data = models.JSONField(default=dict, blank=True, null=True)

    class Meta:
        constraints = [
            CheckConstraint(
                condition=(
                    Q(token_type=TokenTypes.SPL, mint_address__isnull=False)
                    |
                    Q(token_type=TokenTypes.NATIVE, mint_address__isnull=True)
                ),
                name="mint_address_consistency",
            )
        ]

    def __str__(self):
        return f"{self.name} - {self.payment_crypto_price}"


class SolanaPayPaymentCryptoPrice(models.Model):
    amount_in_crypto = models.DecimalField(max_digits=30, decimal_places=18)
    token = models.ForeignKey(solana_payments_settings.PAYMENT_CRYPTO_TOKEN_MODEL, on_delete=models.CASCADE, related_name="crypto_prices")
    meta_data = models.JSONField(default=dict, blank=True)

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{str(self.amount_in_crypto)}"


class OneTimePaymentWallet(models.Model):
    keypair_json = models.JSONField()
    state = models.CharField(
        max_length=50, choices=OneTimeWalletStateTypes.choices, default=OneTimeWalletStateTypes.CREATED
    )
    receiver_address = models.CharField(max_length=60, null=True, blank=True)

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    @property
    def address(self):
        keypair_data = self.keypair_json
        if solana_payments_settings.ONE_TIME_WALLETS_ENCRYPTION_ENABLED:
            key = solana_payments_settings.ONE_TIME_WALLETS_ENCRYPTION_KEY
            encryption_service = WalletEncryptionService(key)
            keypair_data = encryption_service.decrypt(self.keypair_json)

        if isinstance(keypair_data, Keypair):
            keypair = keypair_data
        else:
            keypair = Keypair.from_json(keypair_data)

        return keypair.pubkey()


class SolanaPayment(AbstractSolanaPayment):
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="solana_payments",
    )

    email = models.EmailField(null=True, blank=True)
    label = models.CharField(max_length=255, null=True, blank=True)
    message = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.payment_address
