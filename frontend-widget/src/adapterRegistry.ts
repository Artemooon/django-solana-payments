import {
  WalletAdapterNetwork,
  type WalletAdapter,
} from "@solana/wallet-adapter-base";

export type WalletAdapterFactoryArgs = {
  rpcUrl: string;
  network: WalletAdapterNetwork;
  supportedWallets: string[];
};

export type WalletAdapterFactory = (
  args: WalletAdapterFactoryArgs,
) => WalletAdapter[];

type Registry = Record<string, WalletAdapterFactory>;

declare global {
  interface Window {
    SolanaPaymentWidget?: {
      adapterFactories?: Registry;
      registerWalletAdapterFactory?: (
        name: string,
        factory: WalletAdapterFactory,
      ) => void;
    };
  }
}

function getRegistry(): Registry {
  if (typeof window === "undefined") {
    return {};
  }

  if (!window.SolanaPaymentWidget) {
    window.SolanaPaymentWidget = {};
  }

  if (!window.SolanaPaymentWidget.adapterFactories) {
    window.SolanaPaymentWidget.adapterFactories = {};
  }

  if (!window.SolanaPaymentWidget.registerWalletAdapterFactory) {
    window.SolanaPaymentWidget.registerWalletAdapterFactory = (
      name: string,
      factory: WalletAdapterFactory,
    ) => {
      getRegistry()[name] = factory;
    };
  }

  return window.SolanaPaymentWidget.adapterFactories;
}

export function registerWalletAdapterFactory(
  name: string,
  factory: WalletAdapterFactory,
) {
  getRegistry()[name] = factory;
}

export function resolveWalletAdapterFactory(name?: string | null) {
  if (!name) {
    return null;
  }

  return getRegistry()[name] || null;
}
