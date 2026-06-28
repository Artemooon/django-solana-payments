import {
  PublicKey,
  SystemProgram,
  TransactionMessage,
  VersionedTransaction,
  type Connection,
  type TransactionInstruction,
} from "@solana/web3.js";
import {
  createAssociatedTokenAccountIdempotentInstruction,
  createTransferCheckedInstruction,
  getAssociatedTokenAddress,
  getMint,
} from "@solana/spl-token";

import type {
  PaymentWidgetTokenOption,
  PaymentWidgetTokenType,
  PaymentWidgetTransactionConfig,
} from "./types";

export function buildSolanaPayUrl({
  recipient,
  amount,
  label,
  message,
  mintAddress,
}: {
  recipient: string;
  amount: string;
  label?: string;
  message?: string;
  mintAddress?: string;
}) {
  const url = new URL(`solana:${recipient}`);
  url.searchParams.set("amount", amount);
  if (label) {
    url.searchParams.set("label", label);
  }
  if (message) {
    url.searchParams.set("message", message);
  }
  if (mintAddress) {
    url.searchParams.set("spl-token", mintAddress);
  }
  return url.toString();
}

export function normalizeTokenOption(token: {
  id: number;
  token_type: PaymentWidgetTokenType;
  mint_address?: string | null;
  payment_crypto_price: string;
  name: string;
  symbol: string;
}): PaymentWidgetTokenOption {
  return {
    id: token.id,
    tokenType: token.token_type,
    mintAddress: token.mint_address,
    amount: token.payment_crypto_price,
    name: token.name,
    symbol: token.symbol,
  };
}

export function formatSolAmountForDisplay(amount: string, maxDecimals: number = 4) {
  const trimmed = amount.trim();
  if (!/^\d+(\.\d+)?$/.test(trimmed)) {
    return amount;
  }

  const numericAmount = Number(trimmed);
  if (!Number.isFinite(numericAmount)) {
    return amount;
  }

  return new Intl.NumberFormat("en-US", {
    minimumFractionDigits: 0,
    maximumFractionDigits: maxDecimals,
  }).format(numericAmount);
}

export function solAmountToLamports(amount: string) {
  const trimmed = amount.trim();
  if (!/^\d+(\.\d+)?$/.test(trimmed)) {
    throw new Error("Invalid SOL amount");
  }

  const [wholePart, fractionPart = ""] = trimmed.split(".");
  const paddedFraction = fractionPart.padEnd(9, "0").slice(0, 9);
  return Number(wholePart) * 1_000_000_000 + Number(paddedFraction);
}

export function amountToAtomicUnits(amount: string, decimals: number): bigint {
  const trimmed = amount.trim();
  if (!/^\d+(\.\d+)?$/.test(trimmed)) {
    throw new Error("Invalid token amount");
  }

  const [wholePart, fractionPart = ""] = trimmed.split(".");
  const extraFraction = fractionPart.slice(decimals);
  if (extraFraction && /[1-9]/.test(extraFraction)) {
    throw new Error(`Token amount supports at most ${decimals} decimal places.`);
  }
  const normalizedFraction = fractionPart.slice(0, decimals);
  const paddedFraction = normalizedFraction.padEnd(decimals, "0");

  return BigInt(wholePart + paddedFraction);
}

export async function buildPaymentTransaction(
  connection: Connection,
  senderPublicKey: PublicKey,
  transactionConfig: PaymentWidgetTransactionConfig,
) {
  const tokenType: PaymentWidgetTokenType =
    transactionConfig.tokenType || "NATIVE";
  const recipient = new PublicKey(transactionConfig.recipient);
  const instructions: TransactionInstruction[] = [];

  if (tokenType === "NATIVE") {
    instructions.push(
      SystemProgram.transfer({
        fromPubkey: senderPublicKey,
        toPubkey: recipient,
        lamports: solAmountToLamports(transactionConfig.amount),
      }),
    );
  } else {
    if (!transactionConfig.mintAddress) {
      throw new Error("mintAddress is required for SPL token solana_payments.");
    }

    const mintPublicKey = new PublicKey(transactionConfig.mintAddress);
    const mintInfo = await getMint(connection, mintPublicKey, "confirmed");
    const senderTokenAccount = await getAssociatedTokenAddress(
      mintPublicKey,
      senderPublicKey,
    );
    const recipientTokenAccount = await getAssociatedTokenAddress(
      mintPublicKey,
      recipient,
    );
    const atomicAmount = amountToAtomicUnits(
      transactionConfig.amount,
      mintInfo.decimals,
    );

    instructions.push(
      createAssociatedTokenAccountIdempotentInstruction(
        senderPublicKey,
        recipientTokenAccount,
        recipient,
        mintPublicKey,
      ),
    );
    instructions.push(
      createTransferCheckedInstruction(
        senderTokenAccount,
        mintPublicKey,
        recipientTokenAccount,
        senderPublicKey,
        atomicAmount,
        mintInfo.decimals,
      ),
    );
  }

  const { blockhash, lastValidBlockHeight } =
    await connection.getLatestBlockhash("confirmed");
  const message = new TransactionMessage({
    payerKey: senderPublicKey,
    recentBlockhash: blockhash,
    instructions,
  }).compileToV0Message([]);

  return {
    transaction: new VersionedTransaction(message),
    blockhash,
    lastValidBlockHeight,
  };
}

export async function confirmSignature(
  connection: Connection,
  signature: string,
  blockhash: string,
  lastValidBlockHeight: number,
) {
  await connection.confirmTransaction(
    {
      signature,
      blockhash,
      lastValidBlockHeight,
    },
    "confirmed",
  );
}

type PollPaymentVerificationArgs = {
  tokenType: PaymentWidgetTokenType;
  verifyEndpoint: string;
  mintAddress?: string;
  pollIntervalMs?: number;
  timeoutMs?: number;
  successStatuses?: string[];
};

type VerificationUrlArgs = {
  tokenType: PaymentWidgetTokenType;
  verifyEndpoint: string;
  mintAddress?: string;
};

function getErrorMessage(payload: unknown): string {
  if (
    payload &&
    typeof payload === "object" &&
    "detail" in payload &&
    typeof payload.detail === "string"
  ) {
    return payload.detail;
  }

  return "Payment verification failed.";
}

function isRetriableVerificationResponse(statusCode: number, payload: unknown) {
  if (statusCode !== 409) {
    return false;
  }

  const detail = getErrorMessage(payload).toLowerCase();
  return detail.includes("not confirmed");
}

export async function pollPaymentVerification({
  tokenType,
  verifyEndpoint,
  mintAddress,
  pollIntervalMs = 1500,
  timeoutMs = 45000,
  successStatuses = ["confirmed", "finalized", "processed"],
}: PollPaymentVerificationArgs) {
  const timeoutAt = Date.now() + timeoutMs;
  const normalizedSuccessStatuses = successStatuses.map((status) =>
    status.toLowerCase(),
  );

  while (Date.now() <= timeoutAt) {
    const url = new URL(verifyEndpoint, window.location.origin);
    url.searchParams.set("token_type", tokenType);
    if (tokenType === "SPL" && mintAddress) {
      url.searchParams.set("mint_address", mintAddress);
    }

    const response = await fetch(url.toString(), {
      headers: {
        Accept: "application/json",
      },
    });
    const payload = await response.json().catch(() => null);

    if (response.ok) {
      const status =
        payload &&
        typeof payload === "object" &&
        "status" in payload &&
        typeof payload.status === "string"
          ? payload.status.toLowerCase()
          : "";

      if (normalizedSuccessStatuses.includes(status)) {
        return payload;
      }

      if (status === "expired") {
        throw new Error("Payment expired.");
      }
    } else if (!isRetriableVerificationResponse(response.status, payload)) {
      throw new Error(getErrorMessage(payload));
    }

    await new Promise((resolve) => window.setTimeout(resolve, pollIntervalMs));
  }

  throw new Error("Payment verification timed out.");
}

export function buildVerificationUrl({
  tokenType,
  verifyEndpoint,
  mintAddress,
}: VerificationUrlArgs) {
  const url = new URL(verifyEndpoint, window.location.origin);
  url.searchParams.set("token_type", tokenType);
  if (tokenType === "SPL" && mintAddress) {
    url.searchParams.set("mint_address", mintAddress);
  }
  return url.toString();
}
