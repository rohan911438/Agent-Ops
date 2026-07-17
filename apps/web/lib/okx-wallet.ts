/**
 * Thin wrapper around the OKX Wallet browser extension's injected EIP-1193
 * provider (window.okxwallet). No wagmi/viem — the surface we need
 * (connect + personal_sign) is two `request()` calls.
 */

interface Eip1193Provider {
  request(args: { method: string; params?: unknown[] }): Promise<unknown>;
}

declare global {
  interface Window {
    okxwallet?: Eip1193Provider;
  }
}

export class WalletNotInstalledError extends Error {
  constructor() {
    super("OKX Wallet extension not detected.");
    this.name = "WalletNotInstalledError";
  }
}

/** True only for a genuine EIP-1193 user rejection (code 4001) — e.g. the
 * user dismissed the connect popup or declined to sign. Any other failure
 * (network error, proxy/server error, malformed response) is NOT a wallet
 * rejection and must not be reported to the user as one. */
export function isWalletRejection(error: unknown): boolean {
  return typeof error === "object" && error !== null && "code" in error && (error as { code: unknown }).code === 4001;
}

export function isOkxWalletInstalled(): boolean {
  return typeof window !== "undefined" && typeof window.okxwallet !== "undefined";
}

function getProvider(): Eip1193Provider {
  if (!isOkxWalletInstalled()) {
    throw new WalletNotInstalledError();
  }
  return window.okxwallet as Eip1193Provider;
}

/** Opens the OKX Wallet popup and returns the address the user approved. */
export async function connectWallet(): Promise<string> {
  const provider = getProvider();
  const accounts = (await provider.request({ method: "eth_requestAccounts" })) as string[];
  const address = accounts?.[0];
  if (!address) {
    throw new Error("No account was approved in OKX Wallet.");
  }
  return address;
}

/** Asks the wallet to sign a plaintext message (personal_sign / EIP-191). */
export async function signMessage(address: string, message: string): Promise<string> {
  const provider = getProvider();
  return (await provider.request({
    method: "personal_sign",
    params: [message, address],
  })) as string;
}
