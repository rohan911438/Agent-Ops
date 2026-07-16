import { Badge, Card, CardContent, CardHeader, CardTitle } from "@agentops/ui";
import type { Wallet } from "@agentops/shared-types";
import { serverApiFetch } from "@/lib/server-api";

export default async function WalletSettingsPage() {
  const wallet = await serverApiFetch<Wallet | null>("/settings/wallet");

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-foreground">Wallet</CardTitle>
      </CardHeader>
      <CardContent className="text-sm">
        {wallet ? (
          <div className="flex items-center gap-3">
            <Badge variant="secondary">{wallet.chain}</Badge>
            <span className="font-mono">{wallet.address}</span>
          </div>
        ) : (
          <p className="text-muted-foreground">
            No wallet connected. Connecting a Base wallet reserves identity for future
            on-chain execution proofs and audit verification — nothing is written on-chain
            today.
          </p>
        )}
      </CardContent>
    </Card>
  );
}
