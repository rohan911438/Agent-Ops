import { Card, CardContent, CardHeader, CardTitle } from "./card";
import { cn } from "../lib/utils";

export function MetricCard({
  label,
  value,
  hint,
  tone = "default",
}: {
  label: string;
  value: string;
  hint?: string;
  tone?: "default" | "warning" | "danger";
}) {
  const toneClass =
    tone === "danger"
      ? "text-white font-bold border-b border-white pb-0.5 inline-block"
      : tone === "warning"
        ? "text-zinc-200 underline decoration-zinc-600 decoration-1"
        : "text-foreground";

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-muted-foreground">{label}</CardTitle>
      </CardHeader>
      <CardContent>
        <div className={cn("text-2xl font-semibold tracking-tight", toneClass)}>{value}</div>
        {hint && <p className="mt-1 text-xs text-muted-foreground">{hint}</p>}
      </CardContent>
    </Card>
  );
}
