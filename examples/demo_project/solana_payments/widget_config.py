def build_payment_widget_config(
    api_base_url: str,
    rpc_url: str,
    initiate_payload: dict | None = None,
    verification: dict | None = None,
    wallet_adapter_factory: str | None = None,
    theme: dict | None = None,
    title: str = "Solana Payment",
    caption: str = "Open a compatible wallet and scan the QR code.",
) -> dict:
    return {
        "title": title,
        "caption": caption,
        "api": {
            "baseUrl": api_base_url,
            "initiatePayload": initiate_payload or {},
        },
        "wallet": {
            "enabled": True,
            "rpcUrl": rpc_url,
            "supportedWallets": ["phantom", "solflare"],
            "walletAdapterFactory": wallet_adapter_factory,
        },
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
