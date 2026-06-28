import "./polyfills";
import { mountSolanaPaymentWidget } from "./mount";
import type { PaymentWidgetConfig } from "./types";

function parseConfig(element: HTMLElement): PaymentWidgetConfig {
  const configId = element.dataset.configId;
  if (!configId) {
    throw new Error("Missing data-config-id attribute for Solana payment widget");
  }

  const configNode = document.getElementById(configId);
  if (!configNode?.textContent) {
    throw new Error(`Missing widget config node: ${configId}`);
  }

  return JSON.parse(configNode.textContent) as PaymentWidgetConfig;
}

function autoMountWidgets() {
  const elements = document.querySelectorAll<HTMLElement>("[data-solana-payment-widget]");
  elements.forEach((element) => {
    const config = parseConfig(element);
    mountSolanaPaymentWidget(element, config);
  });
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", autoMountWidgets, { once: true });
} else {
  autoMountWidgets();
}
