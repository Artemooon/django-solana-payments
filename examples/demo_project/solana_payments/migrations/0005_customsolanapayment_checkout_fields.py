from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("solana_payments", "0004_checkoutpayment"),
    ]

    operations = [
        migrations.AddField(
            model_name="customsolanapayment",
            name="email",
            field=models.EmailField(blank=True, max_length=254, null=True),
        ),
        migrations.AddField(
            model_name="customsolanapayment",
            name="label",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="customsolanapayment",
            name="message",
            field=models.TextField(blank=True, null=True),
        ),
    ]
