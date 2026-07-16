import { Card, CardContent, CardHeader, CardTitle } from "@agentops/ui";
import type { Workspace } from "@agentops/shared-types";
import { serverApiFetch } from "@/lib/server-api";

export default async function WorkspaceSettingsPage() {
  const workspace = await serverApiFetch<Workspace>("/settings/workspace");

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-foreground">Workspace</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-4 text-sm">
        <div>
          <div className="text-muted-foreground">Name</div>
          <div className="mt-1 font-medium">{workspace.name}</div>
        </div>
        <div>
          <div className="text-muted-foreground">Slug</div>
          <div className="mt-1 font-medium">{workspace.slug}</div>
        </div>
      </CardContent>
    </Card>
  );
}
