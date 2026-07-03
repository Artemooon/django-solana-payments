import "./polyfills";
import { createRoot } from "react-dom/client";

import { PaymentWidget } from "./PaymentWidget";
import { WidgetProviders } from "./components/WidgetProviders";
import "./styles.css";
import type { PaymentWidgetConfig } from "./types";

export function mountSolanaPaymentWidget(
  container: Element,
  config: PaymentWidgetConfig,
) {
  const root = createRoot(container);
  const supportedWallets = config.wallet?.supportedWallets || [
    "phantom",
    "solflare",
  ];

  root.render(
    <WidgetProviders
      rpcUrl={config.wallet?.rpcUrl || "https://api.mainnet-beta.solana.com/"}
      supportedWallets={supportedWallets}
      walletAdapterFactory={config.wallet?.walletAdapterFactory}
    >
      <PaymentWidget config={config} />
    </WidgetProviders>,
  );
  return root;
}
