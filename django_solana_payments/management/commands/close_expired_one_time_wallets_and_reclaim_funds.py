from django.core.management.base import BaseCommand

from django_solana_payments.services.one_time_wallet_service import OneTimeWalletService


class Command(BaseCommand):
    help = "Close all one-time Solana wallets that are in PAYMENT_EXPIRED state."

    def add_arguments(self, parser):
        parser.add_argument(
            "--sleep",
            type=float,
            default=0,
            help="Sleep interval in seconds between closing each wallet to prevent rate limiting.",
        )

    def handle(self, *args, **options):
        sleep_interval = options["sleep"]
        one_time_wallet_service = OneTimeWalletService()

        self.stdout.write("Starting to close expired one-time wallets...")

        one_time_wallet_service.close_expired_one_time_wallets(
            sleep_interval_seconds=sleep_interval
        )

        self.stdout.write(
            self.style.SUCCESS("Finished closing expired one-time wallets.")
        )
