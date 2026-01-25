from django.contrib import admin

from django_solana_payments.helpers import get_payment_crypto_token_model, get_solana_payment_model
from django_solana_payments.models import SolanaPayPaymentCryptoPrice, OneTimePaymentWallet
from django_solana_payments.services.one_time_wallet_service import one_time_wallet_service


PaymentCryptoToken = get_payment_crypto_token_model()
SolanaPayment = get_solana_payment_model()

@admin.register(PaymentCryptoToken)
class PaymentCryptoTokenAdmin(admin.ModelAdmin):
    def __init__(self, model, admin_site):
        self.list_display = [
            field.name for field in model._meta.fields if field.name in [
                "mint_address", "name", "symbol", "is_active", "token_type", "payment_crypto_price"
            ]
        ]
        self.search_fields = [
            field.name for field in model._meta.fields if field.name in [
                "name", "symbol", "mint_address"
            ]
        ]
        self.list_filter = [
            field.name for field in model._meta.fields if field.name in [
                "token_type", "is_active"
            ]
        ]
        super().__init__(model, admin_site)

class SolanaPayPaymentCryptoPriceInline(admin.TabularInline):
    model = SolanaPayment.crypto_prices.through
    verbose_name = "Solana Payment crypto prices"
    extra = 1
    autocomplete_fields = ["solanapaypaymentcryptoprice"]


@admin.register(SolanaPayment)
class SolanaPayPaymentAdmin(admin.ModelAdmin):
    def __init__(self, model, admin_site):
        self.autocomplete_fields = [
            field.name for field in model._meta.fields if field.name in ["user"]
        ]
        self.list_display = [
            field.name for field in model._meta.fields if field.name in [
                "payment_address", "user", "signature", "status", "created", "updated"
            ]
        ]
        self.readonly_fields = [
            field.name for field in model._meta.fields if field.name in [
                "crypto_prices", "payment_address", "signature"
            ]
        ]
        self.search_fields = [
            field.name for field in model._meta.fields if field.name in [
                "payment_address", "status", "signature", "email"
            ]
        ]
        super().__init__(model, admin_site)

    inlines = [SolanaPayPaymentCryptoPriceInline]


@admin.register(SolanaPayPaymentCryptoPrice)
class SolanaPayPaymentCryptoPriceAdmin(admin.ModelAdmin):
    autocomplete_fields = ("token",)
    list_display = ("token", "amount_in_crypto")
    search_fields = (
        "amount_in_crypto",
    )


@admin.register(OneTimePaymentWallet)
class OneTimePaymentWalletAdmin(admin.ModelAdmin):
    list_display = ("id", "state", "address", "receiver_address", "created", "updated")
    exclude = ("keypair_json",)
    readonly_fields = ("receiver_address", "created", "updated", "address")

    list_filter = ("state",)
    search_fields = ("receiver_address",)


    def save_model(self, request, obj, form, change):
        # Only generate on creation
        if not change and not obj.keypair_json:
            keypair, keypair_json = one_time_wallet_service.generate_one_time_wallet_and_encrypt_if_needed()

            obj.keypair_json = keypair_json
            obj.receiver_address = str(keypair.pubkey())

        super().save_model(request, obj, form, change)
