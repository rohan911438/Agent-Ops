import { notFound } from "next/navigation";
import { Badge, Card, CardContent, CardHeader, CardTitle, StatusPill } from "@agentops/ui";
import type { Agent, ActivityEvent } from "@agentops/shared-types";
import { ApiError } from "@/lib/api-client";
import { serverApiFetch } from "@/lib/server-api";

function formatCents(cents: number) {
  return `$${(cents / 100).toLocaleString(undefined, { maximumFractionDigits: 0 })}`;
}

export default async function AgentDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;

  let agent: Agent;
  try {
    agent = await serverApiFetch<Agent>(`/agents/${id}`);
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) notFound();
    throw err;
  }

  const activity = await serverApiFetch<ActivityEvent[]>(`/activity?agent_id=${id}`);

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">{agent.name}</h1>
          <div className="mt-2 flex items-center gap-2">
            <Badge variant="secondary">{agent.framework}</Badge>
            <StatusPill tone={agent.status === "active" ? "success" : "neutral"}>
              {agent.status}
            </StatusPill>
            <Badge variant={agent.risk_level === "high" ? "destructive" : "outline"}>
              {agent.risk_level} risk
            </Badge>
          </div>
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-muted-foreground">Monthly Cost</CardTitle>
          </CardHeader>
          <CardContent className="text-xl font-semibold">
            {formatCents(agent.monthly_cost_cents)}
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-muted-foreground">Health</CardTitle>
          </CardHeader>
          <CardContent className="text-xl font-semibold">{agent.health_score}/100</CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-muted-foreground">Source</CardTitle>
          </CardHeader>
          <CardContent className="text-xl font-semibold capitalize">{agent.source}</CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-foreground">Activity</CardTitle>
        </CardHeader>
        <CardContent>
          {activity.length === 0 ? (
            <p className="text-sm text-muted-foreground">No activity recorded for this agent.</p>
          ) : (
            <ul className="flex flex-col gap-3">
              {activity.map((event) => (
                <li key={event.id} className="flex items-start justify-between gap-4 text-sm">
                  <div>
                    <span className="font-medium">{event.actor}</span>{" "}
                    <span className="text-muted-foreground">{event.description}</span>
                  </div>
                  <span className="shrink-0 text-xs text-muted-foreground">
                    {new Date(event.created_at).toLocaleString()}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
