import Link from "next/link";
import {
  Badge,
  StatusPill,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
  type StatusPillTone,
} from "@agentops/ui";
import type { Agent } from "@agentops/shared-types";
import { serverApiFetch } from "@/lib/server-api";

const statusTone: Record<Agent["status"], StatusPillTone> = {
  active: "success",
  idle: "neutral",
  error: "danger",
  archived: "neutral",
};

function formatCents(cents: number) {
  return `$${(cents / 100).toLocaleString(undefined, { maximumFractionDigits: 0 })}`;
}

export default async function AgentsPage() {
  const agents = await serverApiFetch<Agent[]>("/agents");

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Agents</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Every AI agent discovered across your workspace.
        </p>
      </div>

      {agents.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          No agents discovered yet. Connect infrastructure from Settings, or run the seed script
          in local dev.
        </p>
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>Framework</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Cost / mo</TableHead>
              <TableHead>Health</TableHead>
              <TableHead>Risk</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {agents.map((agent) => (
              <TableRow key={agent.id}>
                <TableCell>
                  <Link href={`/agents/${agent.id}`} className="font-medium hover:underline">
                    {agent.name}
                  </Link>
                </TableCell>
                <TableCell>
                  <Badge variant="secondary">{agent.framework}</Badge>
                </TableCell>
                <TableCell>
                  <StatusPill tone={statusTone[agent.status]}>{agent.status}</StatusPill>
                </TableCell>
                <TableCell>{formatCents(agent.monthly_cost_cents)}</TableCell>
                <TableCell>{agent.health_score}/100</TableCell>
                <TableCell>
                  <Badge variant={agent.risk_level === "high" ? "destructive" : "outline"}>
                    {agent.risk_level}
                  </Badge>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </div>
  );
}
