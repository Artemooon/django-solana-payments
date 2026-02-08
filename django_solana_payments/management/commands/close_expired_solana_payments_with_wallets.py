from django.core.management import BaseCommand

from django_solana_payments.services.solana_payments_service import (
    SolanaPaymentsService,
)


class Command(BaseCommand):
    help = "Marks expired Solana payments and closes their associated one-time wallets."

    def add_arguments(self, parser):
        parser.add_argument(
            "--sleep",
            type=float,
            default=0,
            help="Sleep interval in seconds between closing each wallet to prevent rate limiting.",
        )

    def handle(self, *args, **options):
        sleep_interval = options["sleep"]
        SolanaPaymentsService().mark_not_finished_solana_payments_as_expired_and_close_wallets_accounts(
            sleep_interval
        )
