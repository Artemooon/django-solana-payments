import { useEffect, useMemo, useState } from "react";
import { WalletReadyState, type WalletName } from "@solana/wallet-adapter-base";
import { useConnection, useWallet } from "@solana/wallet-adapter-react";

import type {
  PaymentWidgetTransactionConfig,
  PaymentWidgetVerificationConfig,
  SupportedWallet,
} from "../types";
import {
  buildVerificationUrl,
  buildPaymentTransaction,
  confirmSignature,
  formatSolAmountForDisplay,
  pollPaymentVerification,
} from "../utils";

type WalletActionBlockProps = {
  supportedWallets: SupportedWallet[];
  transaction: PaymentWidgetTransactionConfig;
  verification?: PaymentWidgetVerificationConfig;
  onNoticeChange?: (notice: {
    kind: "info" | "success" | "error";
    message: string;
    href?: string;
  } | null) => void;
  noticeDismissVersion?: number;
};

function formatWalletAddress(address: string) {
  return "".concat(address.slice(0, 4), "...", address.slice(-4));
}

export function WalletActionBlock({
  supportedWallets,
  transaction,
  verification,
  onNoticeChange,
  noticeDismissVersion = 0,
}: WalletActionBlockProps) {
  const { connection } = useConnection();
  const {
    connected,
    connecting,
    disconnect,
    publicKey,
    select,
    sendTransaction,
    wallet,
    wallets,
  } = useWallet();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [activeWalletName, setActiveWalletName] = useState<string | null>(null);
  const displayAmount = formatSolAmountForDisplay(transaction.amount);
  const displayCurrency = transaction.currencySymbol || "SOL";
  const isWalletBusy = connecting || isSubmitting || activeWalletName !== null;

  useEffect(() => {
    setActiveWalletName(null);
  }, [noticeDismissVersion]);

  const availableWallets = useMemo(() => {
    return wallets.filter((walletEntry) =>
      supportedWallets.includes(walletEntry.adapter.name.toLowerCase() as SupportedWallet),
    );
  }, [supportedWallets, wallets]);

  const publishNotice = (
    kind: "info" | "success" | "error",
    message: string,
    href?: string,
  ) => {
    onNoticeChange?.({ kind, message, href });
  };

  const buildSolscanTransactionUrl = (signature: string) => {
    const endpoint = connection.rpcEndpoint.toLowerCase();
    if (endpoint.includes("devnet")) {
      return `https://solscan.io/tx/${signature}?cluster=devnet`;
    }
    if (endpoint.includes("testnet")) {
      return `https://solscan.io/tx/${signature}?cluster=testnet`;
    }
    return `https://solscan.io/tx/${signature}`;
  };

  const connectWallet = async (walletName: WalletName<string>) => {
    onNoticeChange?.(null);
    setActiveWalletName(walletName);

    try {
      const selectedWallet = availableWallets.find(
        (walletEntry) => walletEntry.adapter.name === walletName,
      );
      if (!selectedWallet) {
        throw new Error("Selected wallet is not available.");
      }

      if (
        selectedWallet.readyState !== WalletReadyState.Installed &&
        selectedWallet.readyState !== WalletReadyState.Loadable
      ) {
        throw new Error(
          `${walletName} is not ready. Check that the wallet extension is installed and enabled.`,
        );
      }

      if (wallet?.adapter.name !== walletName) {
        select(walletName);
      }

      publishNotice("info", `Opening ${walletName}...`);
      await selectedWallet.adapter.connect();
      publishNotice("success", "Wallet connected.");
    } catch (error) {
      publishNotice(
        "error",
        error instanceof Error ? error.message : "Failed to connect wallet.",
      );
      console.error(error);
    } finally {
      setActiveWalletName(null);
    }
  };

  const sendSolTransaction = async () => {
    if (!publicKey) {
      publishNotice("error", "Connect a wallet before sending payment.");
      return;
    }

    setIsSubmitting(true);
    publishNotice("info", "Preparing transaction...");

    try {
      const { transaction: tx, blockhash, lastValidBlockHeight } =
        await buildPaymentTransaction(
        connection,
        publicKey,
        transaction,
      );

      publishNotice("info", "Requesting wallet signature...");
      const signature = await sendTransaction(tx, connection);

      publishNotice("info", "Waiting for confirmation...");
      await confirmSignature(
        connection,
        signature,
        blockhash,
        lastValidBlockHeight,
      );

      if (verification?.enabled && verification.verifyEndpoint) {
        const verificationUrl = buildVerificationUrl({
          tokenType: transaction.tokenType || "NATIVE",
          verifyEndpoint: verification.verifyEndpoint,
          mintAddress: transaction.mintAddress,
        });

        if (verification.redirectOnSuccess) {
          publishNotice("info", "Redirecting to payment result...");
          window.location.href = verificationUrl;
          return;
        }

        publishNotice("info", "Verifying payment...");
        await pollPaymentVerification({
          tokenType: transaction.tokenType || "NATIVE",
          verifyEndpoint: verification.verifyEndpoint,
          mintAddress: transaction.mintAddress,
          pollIntervalMs: verification.pollIntervalMs,
          timeoutMs: verification.timeoutMs,
          successStatuses: verification.successStatuses,
        });
        publishNotice(
          "success",
          "Payment verified.",
          buildSolscanTransactionUrl(signature),
        );
      } else {
        publishNotice(
          "success",
          "Payment submitted to the network.",
          buildSolscanTransactionUrl(signature),
        );
      }
    } catch (error) {
      publishNotice(
        "error",
        error instanceof Error ? error.message : "Transaction failed.",
      );
      console.error(error);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="spw-wallet">
      <div className="spw-wallet-copy">
        <p className="spw-wallet-title">Pay with browser wallet</p>
      </div>

      {connected && publicKey ? (
        <div className="spw-wallet-connected">
          <p className="spw-wallet-badge">
            Connected: {wallet?.adapter.name} {formatWalletAddress(publicKey.toBase58())}
          </p>
          <div className="spw-wallet-actions">
            <button
              className="spw-button spw-button-primary"
              disabled={isSubmitting}
              type="button"
              onClick={sendSolTransaction}
            >
              {isSubmitting
                ? "Sending..."
                : "Pay ".concat(displayAmount, " ", displayCurrency)}
            </button>
            <button
              className="spw-button spw-button-secondary"
              disabled={isSubmitting}
              type="button"
              onClick={() => void disconnect()}
            >
              Disconnect
            </button>
          </div>
        </div>
      ) : (
        <div className="spw-wallet-list">
          {availableWallets.map((walletEntry) => (
            <button
              key={walletEntry.adapter.name}
              className="spw-button spw-button-secondary"
              disabled={isWalletBusy}
              type="button"
              onClick={() => void connectWallet(walletEntry.adapter.name)}
            >
              {activeWalletName === walletEntry.adapter.name
                ? `Opening ${walletEntry.adapter.name}...`
                : `Connect ${walletEntry.adapter.name}`}
            </button>
          ))}
        </div>
      )}

    </div>
  );
}
