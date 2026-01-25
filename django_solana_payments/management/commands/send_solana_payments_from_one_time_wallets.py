from django.core.management import BaseCommand
from django_solana_payments.services.solana_payments_service import SolanaPaymentsService


class Command(BaseCommand):

    def handle(self, *args, **options):
        SolanaPaymentsService().send_solana_payments_from_one_time_wallets()
