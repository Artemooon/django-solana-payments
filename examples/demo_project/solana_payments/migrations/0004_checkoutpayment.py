import payments
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("solana_payments", "0003_alter_custompaymenttoken_payment_crypto_price"),
    ]

    operations = [
        migrations.CreateModel(
            name="CheckoutPayment",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("variant", models.CharField(max_length=255)),
                (
                    "status",
                    models.CharField(
                        choices=payments.PaymentStatus.CHOICES,
                        default=payments.PaymentStatus.WAITING,
                        max_length=10,
                    ),
                ),
                (
                    "fraud_status",
                    models.CharField(
                        choices=payments.FraudStatus.CHOICES,
                        default=payments.FraudStatus.UNKNOWN,
                        max_length=10,
                        verbose_name="fraud check",
                    ),
                ),
                ("fraud_message", models.TextField(blank=True, default="")),
                ("created", models.DateTimeField(auto_now_add=True)),
                ("modified", models.DateTimeField(auto_now=True)),
                ("transaction_id", models.CharField(blank=True, max_length=255)),
                ("currency", models.CharField(max_length=10)),
                (
                    "total",
                    models.DecimalField(decimal_places=2, default="0.0", max_digits=9),
                ),
                (
                    "delivery",
                    models.DecimalField(decimal_places=2, default="0.0", max_digits=9),
                ),
                (
                    "tax",
                    models.DecimalField(decimal_places=2, default="0.0", max_digits=9),
                ),
                ("description", models.TextField(blank=True, default="")),
                ("billing_first_name", models.CharField(blank=True, max_length=256)),
                ("billing_last_name", models.CharField(blank=True, max_length=256)),
                ("billing_address_1", models.CharField(blank=True, max_length=256)),
                ("billing_address_2", models.CharField(blank=True, max_length=256)),
                ("billing_city", models.CharField(blank=True, max_length=256)),
                ("billing_postcode", models.CharField(blank=True, max_length=256)),
                ("billing_country_code", models.CharField(blank=True, max_length=2)),
                ("billing_country_area", models.CharField(blank=True, max_length=256)),
                ("billing_email", models.EmailField(blank=True, max_length=254)),
                (
                    "billing_phone",
                    payments.models.PhoneNumberField(
                        blank=True, max_length=128, region=None
                    ),
                ),
                (
                    "customer_ip_address",
                    models.GenericIPAddressField(blank=True, null=True),
                ),
                ("extra_data", models.TextField(blank=True, default="")),
                ("message", models.TextField(blank=True, default="")),
                ("token", models.CharField(blank=True, default="", max_length=36)),
                (
                    "captured_amount",
                    models.DecimalField(decimal_places=2, default="0.0", max_digits=9),
                ),
            ],
        ),
    ]
