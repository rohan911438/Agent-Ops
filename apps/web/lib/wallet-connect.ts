/**
 * WalletConnect v2 fallback for devices with no OKX Wallet browser
 * extension (every mobile browser, and any desktop without it installed —
 * see okx-wallet.ts, which only supports the injected window.okxwallet
 * provider). Uses @walletconnect/ethereum-provider's own bundled modal
 * (showQrModal) for the QR / mobile-deep-link UI instead of building one,
 * so this stays a thin wrapper exposing the same connect()/sign() shape as
 * okx-wallet.ts.
 */

const CHAIN_ID = 84532; // Base Sepolia — matches apps/api's CHAIN_ID default.

export class WalletConnectNotConfiguredError extends Error {
  constructor() {
    super("NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID is not set.");
    this.name = "WalletConnectNotConfiguredError";
  }
}

let providerPromise: ReturnType<typeof initProvider> | null = null;

async function initProvider() {
  const projectId = process.env.NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID;
  if (!projectId) {
    throw new WalletConnectNotConfiguredError();
  }
  const { EthereumProvider } = await import("@walletconnect/ethereum-provider");
  return EthereumProvider.init({
    projectId,
    chains: [CHAIN_ID],
    showQrModal: true,
    metadata: {
      name: "AgentOps Cloud",
      description: "Enterprise AI Organization Health & Optimization Platform",
      url: "https://agentops-cloud-web.vercel.app",
      icons: [],
    },
  });
}

function getProvider() {
  if (!providerPromise) {
    providerPromise = initProvider();
  }
  return providerPromise;
}

/** Opens the WalletConnect modal (QR on desktop, deep link on mobile) and
 * returns the address the user approved. */
export async function connectWalletConnect(): Promise<string> {
  const provider = await getProvider();
  const accounts = await provider.enable();
  const address = accounts?.[0];
  if (!address) {
    throw new Error("No account was approved in WalletConnect.");
  }
  return address;
}

/** Asks the connected wallet to sign a plaintext message (personal_sign / EIP-191). */
export async function signMessageWalletConnect(address: string, message: string): Promise<string> {
  const provider = await getProvider();
  return (await provider.request({
    method: "personal_sign",
    params: [message, address],
  })) as string;
}

/** Tears down the current session so a later "Connect" starts fresh instead
 * of silently reusing a stale/rejected session object. */
export async function disconnectWalletConnect(): Promise<void> {
  if (!providerPromise) return;
  const provider = await providerPromise;
  await provider.disconnect();
  providerPromise = null;
}
