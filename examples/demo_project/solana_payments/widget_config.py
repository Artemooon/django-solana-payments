from urllib.parse import urlencode


def build_solana_pay_url(
    recipient: str,
    amount: str,
    label: str = "Demo payment",
    message: str = "Scan with a Solana Pay wallet",
    spl_token: str | None = None,
) -> str:
    query_params = {
        "amount": amount,
        "label": label,
        "message": message,
    }
    if spl_token:
        query_params["spl-token"] = spl_token

    query = urlencode(query_params)
    return f"solana:{recipient}?{query}"


def build_payment_widget_config(
    solana_pay_url: str,
    rpc_url: str,
    transaction: dict,
    tokens: dict | None = None,
    verification: dict | None = None,
    wallet_adapter_factory: str | None = None,
    theme: dict | None = None,
    title: str = "Solana Payment",
    caption: str = "Open a compatible wallet and scan the QR code.",
) -> dict:
    return {
        "solanaPayUrl": solana_pay_url,
        "title": title,
        "caption": caption,
        "wallet": {
            "enabled": True,
            "rpcUrl": rpc_url,
            "supportedWallets": ["phantom", "solflare"],
            "walletAdapterFactory": wallet_adapter_factory,
        },
        "transaction": transaction,
        "tokens": tokens or {},
        "verification": verification or {"enabled": False},
        "theme": theme
        or {
            "accent": "#0f766e",
            "background": "#f8fafc",
            "text": "#111827",
            "mutedText": "#475569",
            "borderColor": "#cbd5e1",
            "borderRadius": "20px",
            "fontFamily": '"Helvetica Neue", Arial, sans-serif',
            "shadow": "0 18px 40px rgba(15, 23, 42, 0.08)",
            "payButtonBackground": "#0f8a83",
            "payButtonText": "#ffffff",
            "payButtonBorderColor": "#0f8a83",
            "qrSize": 256,
        },
    }
