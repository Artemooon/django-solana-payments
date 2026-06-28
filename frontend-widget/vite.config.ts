import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  build: {
    target: "es2020",
    outDir: "../examples/demo_project/solana_payments/static/solana_payments/solana-payment-widget",
    emptyOutDir: true,
    cssCodeSplit: false,
    rollupOptions: {
      input: "src/auto-mount.tsx",
      output: {
        entryFileNames: "widget.js",
        assetFileNames: (assetInfo) => {
          if (assetInfo.name?.endsWith(".css")) {
            return "widget.css";
          }
          return "assets/[name]-[hash][extname]";
        },
      },
    },
  },
});
