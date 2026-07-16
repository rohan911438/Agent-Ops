import { MetricCard, Card, CardContent, CardHeader, CardTitle } from "@agentops/ui";
import type { OverviewSummary } from "@agentops/shared-types";
import { serverApiFetch } from "@/lib/server-api";

function formatCents(cents: number) {
  return `$${(cents / 100).toLocaleString(undefined, { maximumFractionDigits: 0 })}`;
}

export default async function OverviewPage() {
  const summary = await serverApiFetch<OverviewSummary>("/overview/summary");

  return (
    <div className="flex flex-col gap-8">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Overview</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          What&apos;s running across your company, right now.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard label="Agents Found" value={String(summary.agents_found)} />
        <MetricCard label="Monthly Cost" value={formatCents(summary.monthly_cost_cents)} />
        <MetricCard
          label="Risks"
          value={String(summary.open_risks)}
          tone={summary.open_risks > 0 ? "danger" : "default"}
        />
        <MetricCard
          label="Optimization Opportunities"
          value={String(summary.optimization_opportunities)}
          tone={summary.optimization_opportunities > 0 ? "warning" : "default"}
        />
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-foreground">Recent Activity</CardTitle>
        </CardHeader>
        <CardContent>
          {summary.recent_activity.length === 0 ? (
            <p className="text-sm text-muted-foreground">No activity recorded yet.</p>
          ) : (
            <ul className="flex flex-col gap-3">
              {summary.recent_activity.map((event) => (
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
