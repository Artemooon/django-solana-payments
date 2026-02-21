from django.core.management import BaseCommand

from django_solana_payments.services.solana_payments_service import (
    SolanaPaymentsService,
)


class Command(BaseCommand):
    help = (
        "Recheck INITIATED payments against on-chain one-time wallet activity and "
        "process missed confirmations."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=200,
            help="Maximum number of latest initiated payments to scan.",
        )
        parser.add_argument(
            "--sleep",
            type=float,
            default=0,
            help="Sleep interval in seconds between payment rechecks.",
        )

    def handle(self, *args, **options):
        limit = options["limit"]
        sleep_interval = options["sleep"]
        summary = SolanaPaymentsService().recheck_initiated_payments_and_process(
            limit=limit,
            sleep_interval_seconds=sleep_interval,
            send_payment_accepted_signal=True,
        )

        self.stdout.write(
            self.style.SUCCESS(
                "Recheck completed: "
                f"scanned={summary['scanned']}, "
                f"reconciled={summary['reconciled']}, "
                f"pending={summary['pending']}, "
                f"failed={summary['failed']}, "
                f"skipped_no_tokens={summary['skipped_no_tokens']}"
            )
        )
