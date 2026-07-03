import type {
  PaymentWidgetApiConfig,
  PaymentWidgetTokenOption,
  PaymentWidgetTokenType,
  PaymentWidgetTransactionConfig,
  PaymentWidgetVerificationConfig,
} from "../types";

export type {
  PaymentWidgetApiConfig,
  PaymentWidgetVerificationConfig,
};

export type ApiBootstrapToken = {
  id: number;
  token_type: PaymentWidgetTokenType;
  mint_address?: string | null;
  payment_crypto_price: string;
  name: string;
  symbol: string;
};

export type ApiBootstrapConfig = {
  transaction: PaymentWidgetTransactionConfig;
  tokens: {
    initialTokens: PaymentWidgetTokenOption[];
  };
  verification: PaymentWidgetVerificationConfig;
};

export type PollPaymentVerificationArgs = {
  tokenType: PaymentWidgetTokenType;
  verifyEndpoint: string;
  mintAddress?: string;
  pollIntervalMs?: number;
  timeoutMs?: number;
  successStatuses?: string[];
};

export type VerificationUrlArgs = {
  tokenType: PaymentWidgetTokenType;
  verifyEndpoint: string;
  mintAddress?: string;
};
