import { Badge, Card, CardContent, CardHeader, CardTitle } from "@agentops/ui";
import type { Recommendation, RecommendationType } from "@agentops/shared-types";
import { serverApiFetch } from "@/lib/server-api";
import { RecommendationActions } from "@/components/recommendation-actions";

const typeLabels: Record<RecommendationType, string> = {
  merge_duplicate: "Merge Duplicate Agents",
  reduce_cost: "Reduce Model Costs",
  unused_agent: "Unused Agents",
  permission_risk: "Permission Risks",
  memory_optimization: "Memory Optimization",
  workflow_optimization: "Workflow Optimization",
  orphaned_agent: "Orphaned Agents",
  model_downgrade: "Model Downgrades",
};

export default async function RecommendationsPage() {
  const recommendations = await serverApiFetch<Recommendation[]>("/recommendations?status_filter=open");

  const grouped = recommendations.reduce<Record<string, Recommendation[]>>((acc, rec) => {
    (acc[rec.type] ??= []).push(rec);
    return acc;
  }, {});

  return (
    <div className="flex flex-col gap-8">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Recommendations</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Ranked, explainable optimizations for your agent fleet.
        </p>
      </div>

      {recommendations.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          No open recommendations. Run a refresh once agents have activity history.
        </p>
      ) : (
        Object.entries(grouped).map(([type, recs]) => (
          <div key={type} className="flex flex-col gap-3">
            <h2 className="text-sm font-medium text-muted-foreground">
              {typeLabels[type as RecommendationType]}
            </h2>
            <div className="grid gap-4 sm:grid-cols-2">
              {recs.map((rec) => (
                <Card key={rec.id}>
                  <CardHeader>
                    <div className="flex items-start justify-between gap-2">
                      <CardTitle className="text-foreground">{rec.title}</CardTitle>
                      <Badge variant="secondary">{rec.impact_estimate}</Badge>
                    </div>
                  </CardHeader>
                  <CardContent className="flex flex-col gap-4">
                    <p className="text-sm text-muted-foreground">{rec.description}</p>
                    <RecommendationActions id={rec.id} />
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>
        ))
      )}
    </div>
  );
}
