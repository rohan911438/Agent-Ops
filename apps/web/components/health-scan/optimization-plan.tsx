import { Badge, Card, CardContent, CardHeader, CardTitle, StatusPill } from "@agentops/ui";
import type { OptimizationPlan, OptimizationPlanItem } from "@agentops/shared-types";

const HORIZONS: { key: keyof Pick<
  OptimizationPlan,
  "immediate_wins" | "thirty_day_plan" | "ninety_day_improvements" | "long_term_architecture"
>; label: string; hint: string }[] = [
  { key: "immediate_wins", label: "Immediate Wins", hint: "This week" },
  { key: "thirty_day_plan", label: "30-Day Plan", hint: "Within 30 days" },
  { key: "ninety_day_improvements", label: "90-Day Improvements", hint: "This quarter" },
  { key: "long_term_architecture", label: "Long-Term Architecture", hint: "Multi-quarter roadmap" },
];

const riskTone: Record<OptimizationPlanItem["risk_level"], "danger" | "warning" | "success"> = {
  high: "danger",
  medium: "warning",
  low: "success",
};

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-[10px] uppercase tracking-wide text-muted-foreground">{label}</div>
      <div className="text-sm font-medium text-foreground">{value}</div>
    </div>
  );
}

function PlanItemCard({ item }: { item: OptimizationPlanItem }) {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-start justify-between gap-2">
          <CardTitle className="text-foreground">{item.title}</CardTitle>
          <div className="flex shrink-0 gap-1.5">
            <Badge variant="outline" className="capitalize">
              {item.priority} priority
            </Badge>
          </div>
        </div>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <p className="text-sm text-muted-foreground">{item.business_value}</p>

        <div className="grid grid-cols-2 gap-3 rounded-md border border-border p-3 sm:grid-cols-3">
          <Stat label="Cost Savings" value={item.estimated_cost_savings} />
          <Stat label="Effort" value={item.estimated_engineering_effort.split(" — ")[0]} />
          <Stat label="Confidence" value={`${item.confidence_score}%`} />
          <Stat label="Timeline" value={item.timeline} />
          <div>
            <div className="text-[10px] uppercase tracking-wide text-muted-foreground">Risk</div>
            <StatusPill tone={riskTone[item.risk_level]} className="mt-0.5 capitalize">
              {item.risk_level}
            </StatusPill>
          </div>
        </div>

        <div className="flex flex-col gap-2 text-sm">
          <div>
            <span className="font-medium text-foreground">Action: </span>
            <span className="text-muted-foreground">{item.recommended_action}</span>
          </div>
          <div>
            <span className="font-medium text-foreground">Expected KPI improvement: </span>
            <span className="text-muted-foreground">{item.expected_kpi_improvement}</span>
          </div>
          <div>
            <span className="font-medium text-foreground">Rollback: </span>
            <span className="text-muted-foreground">{item.rollback_strategy}</span>
          </div>
        </div>

        {item.dependencies.length > 0 && (
          <div>
            <div className="text-xs font-medium text-foreground">Dependencies</div>
            <ul className="mt-1 flex flex-col gap-1 text-xs text-muted-foreground">
              {item.dependencies.map((dep, i) => (
                <li key={i}>• {dep}</li>
              ))}
            </ul>
          </div>
        )}

        <Badge variant="secondary" className="w-fit">
          ROI: {item.expected_roi}
        </Badge>
      </CardContent>
    </Card>
  );
}

export function OptimizationPlanView({ plan }: { plan: OptimizationPlan }) {
  return (
    <div className="flex flex-col gap-6">
      <Card>
        <CardHeader>
          <div className="flex items-start justify-between gap-2">
            <CardTitle className="text-foreground">Optimization Roadmap</CardTitle>
            <Badge>{plan.total_estimated_monthly_savings} recoverable</Badge>
          </div>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">{plan.summary}</CardContent>
      </Card>

      {HORIZONS.map(({ key, label, hint }) => {
        const items = plan[key];
        if (items.length === 0) return null;
        return (
          <div key={key} className="flex flex-col gap-3">
            <div className="flex items-baseline gap-2">
              <h3 className="text-sm font-medium text-foreground">{label}</h3>
              <span className="text-xs text-muted-foreground">{hint}</span>
            </div>
            <div className="grid gap-4 lg:grid-cols-2">
              {items.map((item) => (
                <PlanItemCard key={item.id} item={item} />
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}
