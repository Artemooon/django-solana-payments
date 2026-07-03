import {
  createElement,
  useMemo,
  type ComponentType,
  type ReactNode,
} from "react";
import {
  WalletAdapterNetwork,
  type WalletAdapter,
} from "@solana/wallet-adapter-base";
import { ConnectionProvider, WalletProvider } from "@solana/wallet-adapter-react";
import { PhantomWalletAdapter } from "@solana/wallet-adapter-phantom";

import type { SupportedWallet } from "../types";
import { resolveWalletAdapterFactory } from "../adapterRegistry";
import { SolflareExtensionWalletAdapter } from "./SolflareExtensionWalletAdapter";

type WidgetProvidersProps = {
  children: ReactNode;
  rpcUrl: string;
  supportedWallets: SupportedWallet[];
  walletAdapterFactory?: string;
};

function resolveWalletNetwork(rpcUrl: string) {
  const normalizedRpcUrl = rpcUrl.toLowerCase();

  if (normalizedRpcUrl.includes("devnet")) {
    return WalletAdapterNetwork.Devnet;
  }

  if (normalizedRpcUrl.includes("testnet")) {
    return WalletAdapterNetwork.Testnet;
  }

  return WalletAdapterNetwork.Mainnet;
}

export function WidgetProviders({
  children,
  rpcUrl,
  supportedWallets,
  walletAdapterFactory,
}: WidgetProvidersProps) {
  const ConnectionProviderComponent =
    ConnectionProvider as unknown as ComponentType<{
      endpoint: string;
      children?: ReactNode;
    }>;
  const WalletProviderComponent =
    WalletProvider as unknown as ComponentType<{
      autoConnect?: boolean;
      wallets: readonly WalletAdapter[];
      children?: ReactNode;
    }>;
  const wallets = useMemo<WalletAdapter[]>(() => {
    const adapters: WalletAdapter[] = [];
    const network = resolveWalletNetwork(rpcUrl);

    if (supportedWallets.includes("phantom")) {
      adapters.push(new PhantomWalletAdapter());
    }

    if (supportedWallets.includes("solflare")) {
      adapters.push(new SolflareExtensionWalletAdapter({ network }));
    }

    const externalFactory = resolveWalletAdapterFactory(walletAdapterFactory);
    if (externalFactory) {
      adapters.push(
        ...externalFactory({
          rpcUrl,
          network,
          supportedWallets: [...supportedWallets],
        }),
      );
    }

    const seenNames = new Set<string>();
    return adapters.filter((adapter) => {
      const normalizedName = adapter.name.toLowerCase();
      if (seenNames.has(normalizedName)) {
        return false;
      }
      seenNames.add(normalizedName);
      return true;
    });
  }, [rpcUrl, supportedWallets, walletAdapterFactory]);

  return createElement(
    ConnectionProviderComponent,
    { endpoint: rpcUrl },
    createElement(
      WalletProviderComponent,
      { autoConnect: false, wallets },
      children,
    ),
  );
}
