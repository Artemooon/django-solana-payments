// Reference was taken from - https://github.com/anza-xyz/wallet-adapter/blob/master/packages/wallets/solflare/src/adapter.ts

import type { default as SolflareSdk } from "@solflare-wallet/sdk";
import {
  BaseMessageSignerWalletAdapter,
  WalletConfigError,
  WalletConnectionError,
  WalletDisconnectedError,
  WalletDisconnectionError,
  WalletError,
  WalletLoadError,
  WalletNotConnectedError,
  WalletNotReadyError,
  WalletPublicKeyError,
  WalletReadyState,
  WalletSendTransactionError,
  WalletSignMessageError,
  WalletSignTransactionError,
  isIosAndRedirectable,
  isVersionedTransaction,
  scopePollingDetectionStrategy,
  type SendTransactionOptions,
  type WalletAdapterNetwork,
  type WalletName,
} from "@solana/wallet-adapter-base";
import type { Connection, TransactionVersion, VersionedTransaction } from "@solana/web3.js";
import { PublicKey, type Transaction, type TransactionSignature } from "@solana/web3.js";

type SolflareProviderLike = {
  postMessage?: (message: unknown) => void;
  isSolflare?: boolean;
};

type SolflareWindow = Window & {
  solflare?: SolflareProviderLike | null;
  SolflareApp?: unknown;
};

declare const window: SolflareWindow;

export const SolflareWalletName = "Solflare" as WalletName<"Solflare">;

type SolflareWalletAdapterConfig = {
  network?: WalletAdapterNetwork;
};

type SolflareConstructorConfig = ConstructorParameters<typeof SolflareSdk>[0] & {
  provider?: SolflareProviderLike;
};

function resolveInjectedSolflareProvider() {
  const provider = window.solflare;
  if (provider && typeof provider.postMessage === "function") {
    return provider;
  }
  return undefined;
}

function hasInstalledSolflare() {
  return Boolean(resolveInjectedSolflareProvider() || window.SolflareApp);
}

export class SolflareExtensionWalletAdapter extends BaseMessageSignerWalletAdapter {
  name = SolflareWalletName;
  url = "https://solflare.com";
  icon =
    "data:image/svg+xml;base64,PD94bWwgdmVyc2lvbj0iMS4wIiBlbmNvZGluZz0iVVRGLTgiPz48c3ZnIGlkPSJTIiB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCA1MCA1MCI+PGRlZnM+PHN0eWxlPi5jbHMtMXtmaWxsOiMwMjA1MGE7c3Ryb2tlOiNmZmVmNDY7c3Ryb2tlLW1pdGVybGltaXQ6MTA7c3Ryb2tlLXdpZHRoOi41cHg7fS5jbHMtMntmaWxsOiNmZmVmNDY7fTwvc3R5bGU+PC9kZWZzPjxyZWN0IGNsYXNzPSJjbHMtMiIgeD0iMCIgd2lkdGg9IjUwIiBoZWlnaHQ9IjUwIiByeD0iMTIiIHJ5PSIxMiIvPjxwYXRoIGNsYXNzPSJjbHMtMSIgZD0iTTI0LjIzLDI2LjQybDIuNDYtMi4zOCw0LjU5LDEuNWMzLjAxLDEsNC41MSwyLjg0LDQuNTEsNS40MywwLDEuOTYtLjc1LDMuMjYtMi4yNSw0LjkzbC0uNDYuNS4xNy0xLjE3Yy42Ny00LjI2LS41OC02LjA5LTQuNzItNy40M2wtNC4zLTEuMzhoMFpNMTguMDUsMTEuODVsMTIuNTIsNC4xNy0yLjcxLDIuNTktNi41MS0yLjE3Yy0yLjI1LS43NS0zLjAxLTEuOTYtMy4zLTQuNTF2LS4wOGgwWk0xNy4zLDMzLjA2bDIuODQtMi43MSw1LjM0LDEuNzVjMi44LjkyLDMuNzYsMi4xMywzLjQ2LDUuMThsLTExLjY1LTQuMjJoMFpNMTMuNzEsMjAuOTVjMC0uNzkuNDItMS41NCwxLjEzLTIuMTcuNzUsMS4wOSwyLjA1LDIuMDUsNC4wOSwyLjcxbDQuNDIsMS40Ni0yLjQ2LDIuMzgtNC4zNC0xLjQyYy0yLS42Ny0yLjg0LTEuNjctMi44NC0yLjk2TTI2LjgyLDQyLjg3YzkuMTgtNi4wOSwxNC4xMS0xMC4yMywxNC4xMS0xNS4zMiwwLTMuMzgtMi01LjI2LTYuNDMtNi43MmwtMy4zNC0xLjEzLDkuMTQtOC43Ny0xLjg0LTEuOTYtMi43MSwyLjM4LTEyLjgxLTQuMjJjLTMuOTcsMS4yOS04Ljk3LDUuMDktOC45Nyw4Ljg5LDAsLjQyLjA0LjgzLjE3LDEuMjktMy4zLDEuODgtNC42MywzLjYzLTQuNjMsNS44LDAsMi4wNSwxLjA5LDQuMDksNC41NSw1LjIybDIuNzUuOTItOS41Miw5LjE0LDEuODQsMS45NiwyLjk2LTIuNzEsMTQuNzMsNS4yMmgwWiIvPjwvc3ZnPg==";
  supportedTransactionVersions: ReadonlySet<TransactionVersion> = new Set(["legacy", 0]);

  private _connecting = false;
  private _wallet: SolflareSdk | null = null;
  private _publicKey: PublicKey | null = null;
  private readonly _config: SolflareWalletAdapterConfig;
  private _readyState: WalletReadyState =
    typeof window === "undefined" || typeof document === "undefined"
      ? WalletReadyState.Unsupported
      : hasInstalledSolflare()
        ? WalletReadyState.Installed
        : WalletReadyState.Loadable;

  constructor(config: SolflareWalletAdapterConfig = {}) {
    super();
    this._config = config;

    if (this._readyState !== WalletReadyState.Unsupported) {
      scopePollingDetectionStrategy(() => {
        if (hasInstalledSolflare()) {
          this._readyState = WalletReadyState.Installed;
          this.emit("readyStateChange", this._readyState);
          return true;
        }
        return false;
      });
    }
  }

  get publicKey() {
    return this._publicKey;
  }

  get connecting() {
    return this._connecting;
  }

  get connected() {
    return Boolean(this._wallet?.connected);
  }

  get readyState() {
    return this._readyState;
  }

  async autoConnect() {
    if (!(this.readyState === WalletReadyState.Loadable && isIosAndRedirectable())) {
      await this.connect();
    }
  }

  async connect() {
    try {
      if (this.connected || this.connecting) {
        return;
      }

      if (
        this._readyState !== WalletReadyState.Loadable &&
        this._readyState !== WalletReadyState.Installed
      ) {
        throw new WalletNotReadyError();
      }

      if (this.readyState === WalletReadyState.Loadable && isIosAndRedirectable()) {
        const url = encodeURIComponent(window.location.href);
        const ref = encodeURIComponent(window.location.origin);
        window.location.href = `https://solflare.com/ul/v1/browse/${url}?ref=${ref}`;
        return;
      }

      let SolflareClass: typeof SolflareSdk;
      try {
        SolflareClass = (await import("@solflare-wallet/sdk")).default;
      } catch (error: any) {
        throw new WalletLoadError(error?.message, error);
      }

      let wallet: SolflareSdk;
      try {
        const provider = resolveInjectedSolflareProvider();
        const walletConfig: SolflareConstructorConfig = {
          network: this._config.network,
          // @ts-ignore
          provider,
        };
        wallet = new SolflareClass(
          walletConfig as unknown as ConstructorParameters<typeof SolflareSdk>[0],
        );
      } catch (error: any) {
        throw new WalletConfigError(error?.message, error);
      }

      this._connecting = true;

      if (!wallet.connected) {
        try {
          await wallet.connect();
        } catch (error: any) {
          throw new WalletConnectionError(error?.message, error);
        }
      }

      if (!wallet.publicKey) {
        throw new WalletConnectionError();
      }

      let publicKey: PublicKey;
      try {
        publicKey = new PublicKey(wallet.publicKey.toBytes());
      } catch (error: any) {
        throw new WalletPublicKeyError(error?.message, error);
      }

      wallet.on("disconnect", this._disconnected);
      wallet.on("accountChanged", this._accountChanged);

      this._wallet = wallet;
      this._publicKey = publicKey;
      this.emit("connect", publicKey);
    } catch (error: any) {
      this.emit("error", error);
      throw error;
    } finally {
      this._connecting = false;
    }
  }

  async disconnect() {
    const wallet = this._wallet;
    if (wallet) {
      wallet.off("disconnect", this._disconnected);
      wallet.off("accountChanged", this._accountChanged);
      this._wallet = null;
      this._publicKey = null;

      try {
        await wallet.disconnect();
      } catch (error: any) {
        this.emit("error", new WalletDisconnectionError(error?.message, error));
      }
    }

    this.emit("disconnect");
  }

  async sendTransaction(
    transaction: Transaction | VersionedTransaction,
    connection: Connection,
    options: SendTransactionOptions = {},
  ): Promise<TransactionSignature> {
    try {
      const wallet = this._wallet;
      if (!wallet) {
        throw new WalletNotConnectedError();
      }

      try {
        const { signers, ...sendOptions } = options;

        if (isVersionedTransaction(transaction)) {
          signers?.length && transaction.sign(signers);
        } else {
          transaction = await this.prepareTransaction(transaction, connection, sendOptions);
          signers?.length && transaction.partialSign(...signers);
        }

        sendOptions.preflightCommitment =
          sendOptions.preflightCommitment || connection.commitment;

        return await wallet.signAndSendTransaction(transaction, sendOptions);
      } catch (error: any) {
        if (error instanceof WalletError) {
          throw error;
        }
        throw new WalletSendTransactionError(error?.message, error);
      }
    } catch (error: any) {
      this.emit("error", error);
      throw error;
    }
  }

  async signTransaction<T extends Transaction | VersionedTransaction>(transaction: T): Promise<T> {
    try {
      const wallet = this._wallet;
      if (!wallet) {
        throw new WalletNotConnectedError();
      }

      try {
        return ((await wallet.signTransaction(transaction)) || transaction) as T;
      } catch (error: any) {
        throw new WalletSignTransactionError(error?.message, error);
      }
    } catch (error: any) {
      this.emit("error", error);
      throw error;
    }
  }

  async signAllTransactions<T extends Transaction | VersionedTransaction>(
    transactions: T[],
  ): Promise<T[]> {
    try {
      const wallet = this._wallet;
      if (!wallet) {
        throw new WalletNotConnectedError();
      }

      try {
        return ((await wallet.signAllTransactions(transactions)) || transactions) as T[];
      } catch (error: any) {
        throw new WalletSignTransactionError(error?.message, error);
      }
    } catch (error: any) {
      this.emit("error", error);
      throw error;
    }
  }

  async signMessage(message: Uint8Array): Promise<Uint8Array> {
    try {
      const wallet = this._wallet;
      if (!wallet) {
        throw new WalletNotConnectedError();
      }

      try {
        return await wallet.signMessage(message, "utf8");
      } catch (error: any) {
        throw new WalletSignMessageError(error?.message, error);
      }
    } catch (error: any) {
      this.emit("error", error);
      throw error;
    }
  }

  private _disconnected = () => {
    const wallet = this._wallet;
    if (wallet) {
      wallet.off("disconnect", this._disconnected);
      wallet.off("accountChanged", this._accountChanged);
      this._wallet = null;
      this._publicKey = null;
      this.emit("error", new WalletDisconnectedError());
      this.emit("disconnect");
    }
  };

  private _accountChanged = (nextPublicKey: PublicKey | null) => {
    if (!nextPublicKey || !this._publicKey) {
      return;
    }

    try {
      const normalizedPublicKey = new PublicKey(nextPublicKey.toBytes());
      if (this._publicKey.equals(normalizedPublicKey)) {
        return;
      }
      this._publicKey = normalizedPublicKey;
      this.emit("connect", normalizedPublicKey);
    } catch (error: any) {
      this.emit("error", new WalletPublicKeyError(error?.message, error));
    }
  };
}
