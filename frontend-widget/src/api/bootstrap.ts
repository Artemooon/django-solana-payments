import type {
  ApiBootstrapConfig,
  ApiBootstrapToken,
  PaymentWidgetApiConfig,
  PaymentWidgetVerificationConfig,
} from "./types";
import { buildApiUrl, fetchApiJson, getApiListPayload } from "./base";

export async function buildBootstrapConfigFromApi(
  api: PaymentWidgetApiConfig,
  verificationOverrides?: PaymentWidgetVerificationConfig,
): Promise<ApiBootstrapConfig> {
  const [paymentPayload, tokensPayload] = await Promise.all([
    fetchApiJson(buildApiUrl(api.baseUrl, "initiate/"), {
      method: "POST",
      body: JSON.stringify(api.initiatePayload || {}),
    }),
    fetchApiJson(buildApiUrl(api.baseUrl, "payments-tokens/")),
  ]);

  if (
    !paymentPayload ||
    typeof paymentPayload !== "object" ||
    !("payment_address" in paymentPayload) ||
    typeof paymentPayload.payment_address !== "string"
  ) {
    throw new Error("Payment initiate endpoint did not return payment_address.");
  }

  const paymentAddress = paymentPayload.payment_address;
  const tokenList = getApiListPayload<ApiBootstrapToken>(tokensPayload);
  const initialTokens = tokenList.map((token) => ({
    id: token.id,
    tokenType: token.token_type,
    mintAddress: token.mint_address ?? undefined,
    amount: token.payment_crypto_price,
    name: token.name,
    symbol: token.symbol,
  }));
  const firstToken = initialTokens[0];

  if (!firstToken) {
    throw new Error("Payment tokens endpoint returned no active payment tokens.");
  }

  const initiatePayload = api.initiatePayload || {};
  const label =
    typeof initiatePayload.label === "string" ? initiatePayload.label : undefined;
  const message =
    typeof initiatePayload.message === "string"
      ? initiatePayload.message
      : undefined;

  return {
    transaction: {
      recipient: paymentAddress,
      amount: firstToken.amount,
      label,
      message,
      tokenType: firstToken.tokenType,
      mintAddress:
        firstToken.tokenType === "SPL" ? firstToken.mintAddress || undefined : undefined,
      currencySymbol: firstToken.symbol,
    },
    tokens: {
      initialTokens,
    },
    verification: {
      enabled: verificationOverrides?.enabled ?? true,
      verifyEndpoint: buildApiUrl(api.baseUrl, `verify-transfer/${paymentAddress}`),
      redirectOnSuccess: verificationOverrides?.redirectOnSuccess,
      pollIntervalMs: verificationOverrides?.pollIntervalMs,
      timeoutMs: verificationOverrides?.timeoutMs,
      successStatuses: verificationOverrides?.successStatuses,
    },
  };
}
