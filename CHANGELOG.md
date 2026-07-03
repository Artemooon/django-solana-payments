# Changelog

All notable changes to this project should be documented in this file.

## [1.0.0] - July 3, 2026

### Added

- New checkout UI flow to accept solana payments with the reusable frontend widget.
- `django-payments` integration for embedding the Solana payment widget into `django-payments` checkout flows.
- Root-level convenience imports such as `create_payment`, `create_one_time_wallet`, and `verify_transaction_and_process_payment`.

### Changed

- Renamed the example app from `payments` to `solana_payments`.
- Transaction verification skips transactions that only generates the one-time wallet. If a transaction creates the ATA and sends the payment in the same transaction, it is still accepted as a valid payment.
- Upgraded the Solana dependency to `solana>=0.39.0` and migrated the internal Solana client toward the async `AsyncClient` API with sync-compatible wrappers.
- Moved `confirm_transaction` from `BaseSolanaClient` to `SolanaTransactionSenderClient`.

### Breaking Changes

- The demo app rename from `payments` to `solana_payments` is a breaking change for upgrades that referenced the old app.
- Dropped Python 3.10 support. The library now requires Python 3.11 or newer.
- Dropped Django 4.2 support. The library now targets Django 5.2 or newer.

### Migration Guide

- Update old model references such as `payments.CustomSolanaPayment` and `payments.CustomPaymentToken` to `solana_payments.CustomSolanaPayment` and `solana_payments.CustomPaymentToken`.
- Review any example-project imports, app labels, URL includes, or direct references to the old `payments` module before upgrading to `1.0.0`.
- Upgrade your runtime to Python 3.11+ before installing `solana>=0.39.0`.
- Upgrade Django projects on 4.2 to a supported Django release before adopting `1.0.0`.
