import { Badge, Card, CardContent, CardHeader, CardTitle, StatusPill } from "@agentops/ui";
import type { Wallet } from "@agentops/shared-types";
import { serverApiFetch } from "@/lib/server-api";
import { SignOutButton } from "@/components/auth/sign-out-button";

function shortAddress(address: string) {
  return address.length > 10 ? `${address.slice(0, 6)}…${address.slice(-4)}` : address;
}

function formatDate(value: string | null) {
  if (!value) return "Never";
  return new Date(value).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}

export default async function WalletSettingsPage() {
  const wallet = await serverApiFetch<Wallet | null>("/settings/wallet");

  return (
    <div className="flex flex-col gap-6">
      <Card>
        <CardHeader>
          <CardTitle className="text-foreground">Wallet</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-4 text-sm">
          {wallet ? (
            <>
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">Connected Wallet</span>
                <span className="font-mono">{shortAddress(wallet.address)}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">Chain</span>
                <Badge variant="secondary">{wallet.chain}</Badge>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">Connection Status</span>
                <StatusPill tone="success">Connected</StatusPill>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">Last Verification</span>
                <span>{formatDate(wallet.last_verified_at)}</span>
              </div>
              <div className="flex justify-end border-t border-border/60 pt-4">
                <SignOutButton variant="outline">Disconnect</SignOutButton>
              </div>
            </>
          ) : (
            <p className="text-muted-foreground">
              No wallet connected. This shouldn&apos;t normally happen while signed in — try
              signing out and reconnecting with OKX Wallet.
            </p>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-foreground">Other authentication methods</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">
          Google, Microsoft, GitHub, Okta, and SAML sign-in are reserved as additional ways to
          access this workspace in a future release — OKX Wallet will keep working alongside
          them once they land.
        </CardContent>
      </Card>
    </div>
  );
}
