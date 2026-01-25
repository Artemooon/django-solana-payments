from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from django_solana_payments.choices import TokenTypes
from django_solana_payments.helpers import get_payment_crypto_token_model, get_solana_payment_model
from django_solana_payments.models import SolanaPayPaymentCryptoPrice

SolanaPayment = get_solana_payment_model()


class AllowedCryptoTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_payment_crypto_token_model()
        fields = "__all__"

class SolanaPayPaymentCryptoPriceSerializer(serializers.ModelSerializer):
    token_mint_address = serializers.SerializerMethodField()
    token_type = serializers.SerializerMethodField()

    class Meta:
        model = SolanaPayPaymentCryptoPrice
        fields = ["token_mint_address", "amount_in_crypto", "token_type"]

    def get_token_mint_address(self, obj):
        return obj.token.mint_address

    def get_token_type(self, obj):
        return obj.token.token_type

class SolanaPaymentSerializer(serializers.ModelSerializer):
    crypto_prices = SolanaPayPaymentCryptoPriceSerializer(many=True)

    class Meta:
        model = SolanaPayment
        fields = "__all__"


class VerifySolanaPayTransferSerializer(serializers.ModelSerializer):
    class Meta:
        model = SolanaPayment
        fields = ["status", "payment_address"]


class VerifySolanaPayTransferQuerySerializer(serializers.Serializer):
    mint_address = serializers.CharField(max_length=64, required=False)
    token_type = serializers.ChoiceField(TokenTypes.choices)
    meta_data = serializers.JSONField(
        required=False,
        default=dict,
    )


    def validate(self, attrs):
        if attrs.get("token_type") == TokenTypes.SPL and not attrs.get("mint_address"):
            raise ValidationError("mint_address is required for SPL tokens")

        if attrs.get("token_type") == TokenTypes.NATIVE and attrs.get("mint_address"):
            raise ValidationError("mint_address must be null for native SOL")

        return attrs
