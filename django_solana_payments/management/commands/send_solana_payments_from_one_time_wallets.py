from django.core.management import BaseCommand

from django_solana_payments.services.solana_payments_service import (
    SolanaPaymentsService,
)


class Command(BaseCommand):
    help = "Sends funds from one-time wallets with a CONFIRMED or FINALIZED status to the main wallet."

    def add_arguments(self, parser):
        parser.add_argument(
            "--sleep",
            type=float,
            default=0,
            help="Sleep interval in seconds between sending funds from each wallet to prevent rate limiting.",
        )

    def handle(self, *args, **options):
        sleep_interval = options["sleep"]
        self.stdout.write("Starting to send funds from one-time wallets...")
        SolanaPaymentsService().send_solana_payments_from_one_time_wallets(
            sleep_interval_seconds=sleep_interval
        )
        self.stdout.write(
            self.style.SUCCESS("Finished sending funds from one-time wallets.")
        )
