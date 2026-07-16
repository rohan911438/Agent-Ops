"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import {
  Alert,
  AlertDescription,
  AlertTitle,
  Button,
  Dialog,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@agentops/ui";
import type { SessionRead, WalletNonceResponse } from "@agentops/shared-types";
import { apiFetch, ApiError } from "@/lib/api-client";
import {
  connectWallet,
  isOkxWalletInstalled,
  signMessage,
  WalletNotInstalledError,
} from "@/lib/okx-wallet";

type ConnectStep = "idle" | "connecting" | "awaiting-signature" | "verifying";

const OKX_DOWNLOAD_URL =
  process.env.NEXT_PUBLIC_OKX_WALLET_DOWNLOAD_URL ?? "https://www.okx.com/web3";

const STEP_LABEL: Record<ConnectStep, string> = {
  idle: "Connect OKX Wallet",
  connecting: "Waiting for wallet approval…",
  "awaiting-signature": "Waiting for signature…",
  verifying: "Verifying…",
};

export function ConnectWalletButton({
  size = "lg",
  variant = "default",
  className,
}: {
  size?: "default" | "sm" | "lg";
  variant?: "default" | "outline";
  className?: string;
}) {
  const router = useRouter();
  const [step, setStep] = useState<ConnectStep>("idle");
  const [showInstallDialog, setShowInstallDialog] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleConnect() {
    setError(null);

    if (!isOkxWalletInstalled()) {
      setShowInstallDialog(true);
      return;
    }

    try {
      setStep("connecting");
      const address = await connectWallet();

      const { nonce, message } = await apiFetch<WalletNonceResponse>("/auth/wallet/nonce", {
        method: "POST",
        body: JSON.stringify({ address }),
      });

      setStep("awaiting-signature");
      const signature = await signMessage(address, message);

      setStep("verifying");
      await apiFetch<SessionRead>("/auth/wallet/verify", {
        method: "POST",
        body: JSON.stringify({ address, signature, nonce }),
      });

      router.push("/overview");
      router.refresh();
    } catch (err) {
      if (err instanceof WalletNotInstalledError) {
        setShowInstallDialog(true);
      } else if (err instanceof ApiError) {
        setError("Could not verify that signature — please try connecting again.");
      } else {
        setError("Connection was cancelled or rejected in the wallet.");
      }
      setStep("idle");
    }
  }

  return (
    <>
      <div className="flex flex-col items-center gap-2">
        <Button size={size} variant={variant} className={className} disabled={step !== "idle"} onClick={handleConnect}>
          {STEP_LABEL[step]}
        </Button>
        {error && <p className="text-xs text-destructive">{error}</p>}
      </div>

      <Dialog open={showInstallDialog} onOpenChange={setShowInstallDialog}>
        <DialogHeader>
          <DialogTitle>OKX Wallet is required</DialogTitle>
          <DialogDescription>
            AgentOps Cloud uses the OKX Wallet browser extension to securely verify your
            identity — no password to manage, no separate account to create.
          </DialogDescription>
        </DialogHeader>
        <Alert variant="warning">
          <AlertTitle>Extension not detected</AlertTitle>
          <AlertDescription>
            Install the OKX Wallet extension, then come back to this page and connect again —
            no reload needed.
          </AlertDescription>
        </Alert>
        <DialogFooter>
          <Button variant="outline" onClick={() => setShowInstallDialog(false)}>
            Cancel
          </Button>
          <a href={OKX_DOWNLOAD_URL} target="_blank" rel="noopener noreferrer">
            <Button>Install OKX Wallet</Button>
          </a>
        </DialogFooter>
      </Dialog>
    </>
  );
}
