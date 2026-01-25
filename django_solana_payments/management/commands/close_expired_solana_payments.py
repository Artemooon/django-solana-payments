from django.core.management import BaseCommand

from django_solana_payments.services.solana_payments_service import SolanaPaymentsService


class Command(BaseCommand):

    def handle(self, *args, **options):
        SolanaPaymentsService().mark_not_finished_solana_payments_as_expired()
