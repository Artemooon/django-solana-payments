from unittest.mock import patch

import pytest
from django.core.management import call_command

pytestmark = pytest.mark.django_db


@patch(
    "django_solana_payments.management.commands.recheck_initiated_solana_payments.SolanaPaymentsService.recheck_initiated_payments_and_process"
)
def test_recheck_initiated_solana_payments_command_calls_service(mock_recheck):
    mock_recheck.return_value = {
        "scanned": 10,
        "reconciled": 3,
        "pending": 6,
        "failed": 1,
        "skipped_no_tokens": 0,
    }

    call_command("recheck_initiated_solana_payments", "--limit", "25", "--sleep", "0.2")

    mock_recheck.assert_called_once_with(
        limit=25,
        sleep_interval_seconds=0.2,
        send_payment_accepted_signal=True,
    )


@patch(
    "django_solana_payments.management.commands.close_expired_solana_payments_with_wallets.SolanaPaymentsService.mark_not_finished_solana_payments_as_expired_and_close_wallets_accounts"
)
def test_close_expired_solana_payments_with_wallets_command_calls_service(
    mock_mark_expired,
):
    call_command("close_expired_solana_payments_with_wallets", "--sleep", "0.3")

    mock_mark_expired.assert_called_once_with(0.3)


@patch(
    "django_solana_payments.management.commands.send_solana_payments_from_one_time_wallets.SolanaPaymentsService.send_solana_payments_from_one_time_wallets"
)
def test_send_solana_payments_from_one_time_wallets_command_calls_service(
    mock_send_funds,
):
    call_command("send_solana_payments_from_one_time_wallets", "--sleep", "0.4")

    mock_send_funds.assert_called_once_with(sleep_interval_seconds=0.4)


@patch(
    "django_solana_payments.management.commands.close_expired_one_time_wallets_and_reclaim_funds.OneTimeWalletService.close_expired_one_time_wallets"
)
def test_close_expired_one_time_wallets_and_reclaim_funds_command_calls_service(
    mock_close_wallets,
):
    call_command("close_expired_one_time_wallets_and_reclaim_funds", "--sleep", "0.5")

    mock_close_wallets.assert_called_once_with(sleep_interval_seconds=0.5)
