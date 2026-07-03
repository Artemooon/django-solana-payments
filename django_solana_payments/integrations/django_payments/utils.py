from urllib.parse import urlencode

from django_solana_payments.choices import TokenTypes


def build_solana_pay_url(
    recipient: str,
    amount: str,
    label: str,
    message: str,
    spl_token: str | None = None,
) -> str:
    query_params = {
        "amount": amount,
        "label": label,
        "message": message,
    }
    if spl_token:
        query_params["spl-token"] = spl_token

    return f"solana:{recipient}?{urlencode(query_params)}"


def build_payment_widget_config(
    *,
    solana_pay_url: str,
    rpc_url: str,
    recipient: str,
    amount: str,
    token_type: str,
    mint_address: str | None,
    currency_symbol: str,
    verify_endpoint: str,
    tokens: dict | None,
    title: str,
    caption: str,
    supported_wallets: list[str],
    wallet_adapter_factory: str | None,
    poll_interval_ms: int,
    timeout_ms: int,
    success_statuses: list[str],
    theme: dict | None = None,
) -> dict:
    transaction = {
        "recipient": recipient,
        "amount": amount,
        "tokenType": token_type,
        "currencySymbol": currency_symbol,
    }
    if token_type == TokenTypes.SPL and mint_address:
        transaction["mintAddress"] = mint_address

    return {
        "solanaPayUrl": solana_pay_url,
        "title": title,
        "caption": caption,
        "wallet": {
            "enabled": True,
            "rpcUrl": rpc_url,
            "supportedWallets": supported_wallets,
            "walletAdapterFactory": wallet_adapter_factory,
        },
        "transaction": transaction,
        "tokens": tokens or {},
        "verification": {
            "enabled": True,
            "verifyEndpoint": verify_endpoint,
            "redirectOnSuccess": True,
            "pollIntervalMs": poll_interval_ms,
            "timeoutMs": timeout_ms,
            "successStatuses": success_statuses,
        },
        "theme": theme or {},
    }
