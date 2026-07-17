"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Alert,
  AlertDescription,
  AlertTitle,
  Badge,
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Stepper,
  type StepState,
} from "@agentops/ui";
import type { HealthScan, Recommendation } from "@agentops/shared-types";
import { apiFetch } from "@/lib/api-client";
import { getReportVerification } from "@/lib/verification";
import { RecommendationActions } from "@/components/recommendation-actions";
import { OptimizationPlanView } from "@/components/health-scan/optimization-plan";
import { VerificationCard } from "@/components/health-scan/verification-card";

const STEP_ORDER = ["pending", "parsing", "analyzing", "generating_report", "completed"] as const;

const STEP_LABELS: Record<(typeof STEP_ORDER)[number], string> = {
  pending: "Queued",
  parsing: "Parsing agent definitions",
  analyzing: "Analyzing fleet & running recommendation engine",
  generating_report: "Generating executive report",
  completed: "Complete",
};

function isTerminal(status: HealthScan["status"]) {
  return status === "completed" || status === "failed";
}

function formatCents(cents: number) {
  return `$${(cents / 100).toLocaleString(undefined, { maximumFractionDigits: 0 })}`;
}

export function ScanStatus({ initialScan }: { initialScan: HealthScan }) {
  const queryClient = useQueryClient();

  const { data: scan } = useQuery({
    queryKey: ["scan", initialScan.id],
    queryFn: () => apiFetch<HealthScan>(`/scans/${initialScan.id}`),
    initialData: initialScan,
    refetchInterval: (query) => (isTerminal(query.state.data?.status ?? "pending") ? false : 1500),
  });

  const { data: recommendations } = useQuery({
    queryKey: ["scan-recommendations", scan.id],
    queryFn: () => apiFetch<Recommendation[]>("/recommendations?status_filter=open"),
    enabled: scan.status === "completed",
  });

  const { data: verification } = useQuery({
    queryKey: ["scan-verification", scan.id],
    queryFn: () => getReportVerification(scan.id),
    enabled: scan.status === "completed",
  });

  async function retry() {
    await apiFetch(`/scans/${scan.id}/start`, { method: "POST" });
    await queryClient.invalidateQueries({ queryKey: ["scan", scan.id] });
  }

  if (scan.status === "failed") {
    return (
      <Alert variant="destructive">
        <AlertTitle>Scan failed</AlertTitle>
        <AlertDescription>
          {scan.error_message ?? "Something went wrong while running this scan."}
        </AlertDescription>
        <Button size="sm" className="mt-3" onClick={retry}>
          Retry
        </Button>
      </Alert>
    );
  }

  if (scan.status !== "completed") {
    const currentIndex = STEP_ORDER.indexOf(scan.status);
    const steps = STEP_ORDER.slice(0, 4).map((key, i) => ({
      label: STEP_LABELS[key],
      description: i === currentIndex ? (scan.current_step ?? undefined) : undefined,
      state: (i < currentIndex ? "complete" : i === currentIndex ? "active" : "pending") as StepState,
    }));
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-foreground">Scanning {scan.source_label}</CardTitle>
        </CardHeader>
        <CardContent>
          <Stepper steps={steps} />
        </CardContent>
      </Card>
    );
  }

  const report = scan.executive_report;
  const scanRecommendations = (recommendations ?? []).filter(
    (rec) => rec.agent_id && scan.agent_ids.includes(rec.agent_id),
  );

  return (
    <div className="flex flex-col gap-8">
      {scan.summary && (
        <div className="grid gap-4 sm:grid-cols-4">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-muted-foreground">Agents Found</CardTitle>
            </CardHeader>
            <CardContent className="text-xl font-semibold">{scan.summary.agent_count}</CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-muted-foreground">Est. Monthly Spend</CardTitle>
            </CardHeader>
            <CardContent className="text-xl font-semibold">
              {formatCents(scan.summary.monthly_cost_cents)}
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-muted-foreground">Frameworks</CardTitle>
            </CardHeader>
            <CardContent className="text-xl font-semibold">
              {Object.keys(scan.summary.frameworks).length}
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-muted-foreground">Opportunities Found</CardTitle>
            </CardHeader>
            <CardContent className="text-xl font-semibold">
              {scan.summary.duplicate_count +
                scan.summary.orphaned_count +
                scan.summary.high_risk_count +
                scan.summary.unused_count +
                scan.summary.model_downgrade_count}
            </CardContent>
          </Card>
        </div>
      )}

      {report && (
        <Card>
          <CardHeader>
            <div className="flex items-start justify-between gap-2">
              <CardTitle className="text-foreground">Executive Summary</CardTitle>
              <Badge
                variant={
                  report.health_score >= 80 ? "secondary" : report.health_score >= 50 ? "outline" : "destructive"
                }
              >
                Health {report.health_score}/100
              </Badge>
            </div>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            <p className="text-sm text-muted-foreground">{report.executive_summary}</p>
            <p className="text-sm text-muted-foreground">{report.organization_overview}</p>
          </CardContent>
        </Card>
      )}

      <VerificationCard verification={verification ?? null} />

      {report && (
        <div className="grid gap-4 lg:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle className="text-foreground">Cost Analysis</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col gap-2">
              <p className="text-sm text-muted-foreground">{report.cost_analysis.summary}</p>
              {report.cost_analysis.model_downgrade_suggestions.length > 0 && (
                <ul className="flex flex-col gap-1 text-sm text-muted-foreground">
                  {report.cost_analysis.model_downgrade_suggestions.map((item, i) => (
                    <li key={i}>• {item}</li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle className="text-foreground">Security Risks</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col gap-2">
              <p className="text-sm text-muted-foreground">{report.security_risks.summary}</p>
              {report.security_risks.high_risk_agents.length > 0 && (
                <ul className="flex flex-col gap-1 text-sm text-muted-foreground">
                  {report.security_risks.high_risk_agents.map((item, i) => (
                    <li key={i}>• {item}</li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle className="text-foreground">Operational Risks</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col gap-2">
              <p className="text-sm text-muted-foreground">{report.operational_risks.summary}</p>
              {[...report.operational_risks.orphaned_agents, ...report.operational_risks.redundant_workflows]
                .length > 0 && (
                <ul className="flex flex-col gap-1 text-sm text-muted-foreground">
                  {report.operational_risks.orphaned_agents.map((item, i) => (
                    <li key={`o-${i}`}>• {item}</li>
                  ))}
                  {report.operational_risks.redundant_workflows.map((item, i) => (
                    <li key={`r-${i}`}>• {item}</li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle className="text-foreground">Optimization Opportunities</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col gap-2">
              <p className="text-sm text-muted-foreground">{report.optimization_opportunities.summary}</p>
              {report.optimization_opportunities.merge_candidates.length > 0 && (
                <ul className="flex flex-col gap-1 text-sm text-muted-foreground">
                  {report.optimization_opportunities.merge_candidates.map((item, i) => (
                    <li key={i}>• {item}</li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      {report && (
        <Card>
          <CardHeader>
            <CardTitle className="text-foreground">Business Impact</CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground">{report.business_impact}</CardContent>
        </Card>
      )}

      {report && (
        <div className="flex flex-col gap-3">
          <h2 className="text-sm font-medium text-muted-foreground">Top 5 Highest-ROI Actions</h2>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {report.priority_actions.map((action, i) => (
              <Card key={i}>
                <CardHeader>
                  <div className="flex items-start justify-between gap-2">
                    <CardTitle className="text-foreground">
                      {i + 1}. {action.title}
                    </CardTitle>
                  </div>
                </CardHeader>
                <CardContent className="flex flex-col gap-3">
                  <p className="text-sm text-muted-foreground">{action.rationale}</p>
                  <Badge variant="secondary" className="w-fit">
                    {action.estimated_impact}
                  </Badge>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}

      {scan.optimization_plan && <OptimizationPlanView plan={scan.optimization_plan} />}

      <div className="flex flex-col gap-3">
        <h2 className="text-sm font-medium text-muted-foreground">Optimization Recommendations</h2>
        {scanRecommendations.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            No open recommendations for the agents this scan found.
          </p>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2">
            {scanRecommendations.map((rec) => (
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
        )}
      </div>
    </div>
  );
}
