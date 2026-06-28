import { useEffect, useMemo, useState, type CSSProperties } from "react";

import { SolanaPayQrCode } from "./components/SolanaPayQrCode";
import { WalletActionBlock } from "./components/WalletActionBlock";
import type {
  PaymentWidgetConfig,
  PaymentWidgetTokenOption,
  PaymentWidgetTransactionConfig,
} from "./types";
import { buildSolanaPayUrl, normalizeTokenOption } from "./utils";

type PaymentWidgetProps = {
  config: PaymentWidgetConfig;
};

type WidgetNotice = {
  kind: "info" | "success" | "error";
  message: string;
  href?: string;
};

type WidgetStyleVars = CSSProperties & {
  "--spw-accent"?: string;
  "--spw-background"?: string;
  "--spw-text"?: string;
  "--spw-muted-text"?: string;
  "--spw-border"?: string;
  "--spw-radius"?: string;
  "--spw-font-family"?: string;
  "--spw-shadow"?: string;
  "--spw-pay-button-background"?: string;
  "--spw-pay-button-text"?: string;
  "--spw-pay-button-border"?: string;
};

export function PaymentWidget({ config }: PaymentWidgetProps) {
  const { theme = {}, transaction, wallet, tokens } = config;
  const initialTokens = tokens?.initialTokens || [];
  const [availableTokens, setAvailableTokens] = useState<PaymentWidgetTokenOption[]>(
    initialTokens,
  );
  const [selectedTokenId, setSelectedTokenId] = useState<number | null>(
    initialTokens[0]?.id || null,
  );
  const [tokensError, setTokensError] = useState("");
  const [walletNotice, setWalletNotice] = useState<WidgetNotice | null>(null);
  const [walletNoticeDismissVersion, setWalletNoticeDismissVersion] = useState(0);

  useEffect(() => {
    setAvailableTokens(initialTokens);
    setSelectedTokenId(initialTokens[0]?.id || null);
  }, [initialTokens]);

  useEffect(() => {
    const tokensEndpoint = tokens?.endpoint;
    if (!tokensEndpoint) {
      return;
    }

    let isCancelled = false;

    const loadTokens = async () => {
      try {
        setTokensError("");
        const response = await fetch(tokensEndpoint, {
          headers: {
            Accept: "application/json",
          },
        });
        if (!response.ok) {
          throw new Error("Failed to load payment tokens.");
        }

        const payload = await response.json();
        const endpointTokens = Array.isArray(payload)
          ? payload.map(normalizeTokenOption)
          : [];
        const paymentTokenIds = new Set(initialTokens.map((token) => token.id));
        const normalizedTokens =
          initialTokens.length > 0
            ? endpointTokens
                .filter((token) => paymentTokenIds.has(token.id))
                .map((token) => {
                  const snapshotToken = initialTokens.find(
                    (initialToken) => initialToken.id === token.id,
                  );
                  return snapshotToken
                    ? {
                        ...token,
                        amount: snapshotToken.amount,
                        tokenType: snapshotToken.tokenType,
                        mintAddress: snapshotToken.mintAddress,
                      }
                    : token;
                })
            : endpointTokens;

        if (!isCancelled) {
          setAvailableTokens(normalizedTokens);
          setSelectedTokenId((currentTokenId) => {
            if (
              currentTokenId &&
              normalizedTokens.some((token) => token.id === currentTokenId)
            ) {
              return currentTokenId;
            }
            return normalizedTokens[0]?.id || null;
          });
        }
      } catch (error) {
        if (!isCancelled) {
          setTokensError(
            error instanceof Error
              ? error.message
              : "Failed to load payment tokens.",
          );
          setWalletNotice({
            kind: "error",
            message:
              error instanceof Error
                ? error.message
                : "Failed to load payment tokens.",
          });
        }
      }
    };

    void loadTokens();

    return () => {
      isCancelled = true;
    };
  }, [initialTokens, tokens?.endpoint]);

  const styleVars: WidgetStyleVars = {
    "--spw-accent": theme.accent,
    "--spw-background": theme.background,
    "--spw-text": theme.text,
    "--spw-muted-text": theme.mutedText,
    "--spw-border": theme.borderColor,
    "--spw-radius": theme.borderRadius,
    "--spw-font-family": theme.fontFamily,
    "--spw-shadow": theme.shadow,
    "--spw-pay-button-background": theme.payButtonBackground,
    "--spw-pay-button-text": theme.payButtonText,
    "--spw-pay-button-border": theme.payButtonBorderColor,
  };

  const selectedToken = useMemo(() => {
    if (!availableTokens.length) {
      return null;
    }

    if (selectedTokenId === null) {
      return availableTokens[0];
    }

    return (
      availableTokens.find((token) => token.id === selectedTokenId) ||
      availableTokens[0]
    );
  }, [availableTokens, selectedTokenId]);

  const resolvedTransaction: PaymentWidgetTransactionConfig | undefined = useMemo(() => {
    if (!transaction) {
      return undefined;
    }

    if (!selectedToken) {
      return transaction;
    }

    return {
      ...transaction,
      amount: selectedToken.amount,
      tokenType: selectedToken.tokenType,
      mintAddress:
        selectedToken.tokenType === "SPL" ? selectedToken.mintAddress || undefined : undefined,
      currencySymbol: selectedToken.symbol,
    };
  }, [selectedToken, transaction]);

  const resolvedSolanaPayUrl = useMemo(() => {
    if (!resolvedTransaction) {
      return config.solanaPayUrl;
    }

    return buildSolanaPayUrl({
      recipient: resolvedTransaction.recipient,
      amount: resolvedTransaction.amount,
      label: resolvedTransaction.label,
      message: resolvedTransaction.message,
      mintAddress:
        resolvedTransaction.tokenType === "SPL"
          ? resolvedTransaction.mintAddress
          : undefined,
    });
  }, [config.solanaPayUrl, resolvedTransaction]);

  const activeNotice = useMemo(() => {
    if (walletNotice) {
      return walletNotice;
    }
    if (tokensError) {
      return {
        kind: "error" as const,
        message: tokensError,
      };
    }
    return null;
  }, [tokensError, walletNotice]);

  return (
    <section className="spw-card" style={styleVars}>
      <div className="spw-copy">
          <h2 className="spw-eyebrow">{config.title || "Solana Payment"}</h2>
        <p className="spw-caption">
          {config.caption || "Open a compatible wallet and scan the QR code."}
        </p>
      </div>
      {availableTokens.length > 0 ? (
        <div className="spw-token-picker">
          <label className="spw-token-label" htmlFor="spw-token-select">
            Select a token to pay with
          </label>
          <select
            id="spw-token-select"
            className="spw-token-select"
            value={selectedToken?.id || ""}
            onChange={(event) => {
              const nextValue = Number(event.target.value);
              setSelectedTokenId(Number.isFinite(nextValue) ? nextValue : null);
            }}
          >
            {availableTokens.map((token) => (
              <option key={token.id} value={token.id}>
                {token.symbol} · {token.amount}
              </option>
            ))}
          </select>
        </div>
      ) : null}
      <SolanaPayQrCode
        solanaPayUrl={resolvedSolanaPayUrl}
        size={theme.qrSize || 256}
      />
      {wallet?.enabled && resolvedTransaction ? (
        <WalletActionBlock
          supportedWallets={wallet.supportedWallets || ["phantom", "solflare"]}
          transaction={resolvedTransaction}
          verification={config.verification}
          onNoticeChange={setWalletNotice}
          noticeDismissVersion={walletNoticeDismissVersion}
        />
      ) : null}
      {activeNotice ? (
        <div className="spw-alert-stack" aria-live="polite" aria-atomic="true">
          <div className={`spw-alert spw-alert-${activeNotice.kind}`} role="status">
            <span className="spw-alert-indicator" aria-hidden="true" />
            <span className="spw-alert-message">{activeNotice.message}</span>
            {activeNotice.href ? (
              <a
                className="spw-alert-link"
                href={activeNotice.href}
                rel="noreferrer"
                target="_blank"
              >
                Transaction link
              </a>
            ) : null}
            <button
              className="spw-alert-dismiss"
              type="button"
              aria-label="Dismiss message"
              onClick={() => {
                setWalletNotice(null);
                setTokensError("");
                setWalletNoticeDismissVersion((currentVersion) => currentVersion + 1);
              }}
            >
              Close
            </button>
          </div>
        </div>
      ) : null}
    </section>
  );
}
