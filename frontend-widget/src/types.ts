export type PaymentWidgetTheme = {
  accent?: string;
  background?: string;
  text?: string;
  mutedText?: string;
  borderColor?: string;
  borderRadius?: string;
  fontFamily?: string;
  shadow?: string;
  payButtonBackground?: string;
  payButtonText?: string;
  payButtonBorderColor?: string;
  qrSize?: number;
};

export type BuiltInSupportedWallet = "phantom" | "solflare";
export type SupportedWallet = BuiltInSupportedWallet | (string & {});
export type PaymentWidgetTokenType = "NATIVE" | "SPL";

export type PaymentWidgetWalletConfig = {
  enabled?: boolean;
  rpcUrl: string;
  supportedWallets?: SupportedWallet[];
  walletAdapterFactory?: string;
};

export type PaymentWidgetTransactionConfig = {
  recipient: string;
  amount: string;
  label?: string;
  message?: string;
  tokenType?: PaymentWidgetTokenType;
  mintAddress?: string;
  currencySymbol?: string;
};

export type PaymentWidgetTokenOption = {
  id: number;
  tokenType: PaymentWidgetTokenType;
  mintAddress?: string | null;
  amount: string;
  name: string;
  symbol: string;
};

export type PaymentWidgetTokensConfig = {
  initialTokens?: PaymentWidgetTokenOption[];
};

export type PaymentWidgetVerificationConfig = {
  enabled?: boolean;
  verifyEndpoint?: string;
  redirectOnSuccess?: boolean;
  pollIntervalMs?: number;
  timeoutMs?: number;
  successStatuses?: string[];
};

export type PaymentWidgetConfig = {
  solanaPayUrl: string;
  title?: string;
  caption?: string;
  mountId?: string;
  theme?: PaymentWidgetTheme;
  wallet?: PaymentWidgetWalletConfig;
  transaction?: PaymentWidgetTransactionConfig;
  tokens?: PaymentWidgetTokensConfig;
  verification?: PaymentWidgetVerificationConfig;
};
