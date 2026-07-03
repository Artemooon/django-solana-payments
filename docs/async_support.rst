Async Support
=============

`django-solana-payments` uses `solana.rpc.async_api.AsyncClient` under the hood, as
`solana-py removed support for the sync client <https://michaelhly.com/solana-py/rpc/api/>`_.

Library keeps sync-friendly wrappers, but also exposes async methods for operations that
communicate with the Solana blockchain.

When to use async methods
-------------------------

Use async methods when your project already runs in async context, for example:

- async Django views
- ASGI workers
- async background tasks
- other code paths where you already use `await`

Async methods use `a...` prefix.

Examples:

- `SolanaTransactionSenderClient.asend_transaction`
- `SolanaTransactionSenderClient.aconfirm_transaction`
- `SolanaTransactionSenderClient.asend_transaction_with_retry`
- `SolanaTokenClient.aget_balance`
- `SolanaTokenClient.aget_account_info`
- `SolanaTokenClient.aget_token_supply`
- `SolanaTransactionQueryClient.aget_transaction`
- `SolanaTransactionQueryClient.aget_signatures_for_address`

Example
-------

.. code-block:: python

    from django_solana_payments.solana.base_solana_client import BaseSolanaClient
    from django_solana_payments.solana.solana_token_client import SolanaTokenClient
    from django_solana_payments.solana.solana_transaction_query_client import (
        SolanaTransactionQueryClient,
    )
    from django_solana_payments.solana.solana_transaction_sender_client import (
        SolanaTransactionSenderClient,
    )

    base_client = BaseSolanaClient()
    token_client = SolanaTokenClient(base_client)
    tx_query_client = SolanaTransactionQueryClient(base_client)
    tx_sender_client = SolanaTransactionSenderClient(base_client)

    balance = await token_client.aget_balance(wallet_pubkey)
    account_info = await token_client.aget_account_info(wallet_pubkey)
    transaction = await tx_query_client.aget_transaction(signature)
    confirmation = await tx_sender_client.aconfirm_transaction(signature)

Notes
-----

`BaseSolanaClient` provides shared RPC client configuration and sync/async bridging utilities.

`SolanaTransactionSenderClient` owns transaction send and confirmation methods.

`SolanaTransactionBuilder` builds transactions, but does not expose async methods itself.

See :doc:`installation` for setup and :doc:`api_reference` for full client reference.
