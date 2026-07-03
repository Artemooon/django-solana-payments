import type {
  PollPaymentVerificationArgs,
  VerificationUrlArgs,
} from "./types";

function getVerificationErrorMessage(payload: unknown): string {
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

  const detail = getVerificationErrorMessage(payload).toLowerCase();
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
      throw new Error(getVerificationErrorMessage(payload));
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
