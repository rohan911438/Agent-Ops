import Link from "next/link";
import { Badge, Button, Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@agentops/ui";
import type { HealthScan } from "@agentops/shared-types";
import { serverApiFetch } from "@/lib/server-api";
import { PricingNote } from "@/components/pricing-note";

const statusTone: Record<HealthScan["status"], "success" | "warning" | "danger" | "neutral"> = {
  pending: "neutral",
  parsing: "warning",
  analyzing: "warning",
  generating_report: "warning",
  completed: "success",
  failed: "danger",
};

export default async function HealthScanPage() {
  const scans = await serverApiFetch<HealthScan[]>("/scans");

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Health Scan</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Discover your agent fleet and get an Executive Health Report.
          </p>
        </div>
        <Link href="/health-scan/new">
          <Button size="lg">New Scan</Button>
        </Link>
      </div>

      <PricingNote />

      {scans.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          No scans yet — start one to see your agent fleet&apos;s cost, risk, and optimization
          opportunities.
        </p>
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Source</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Agents Found</TableHead>
              <TableHead>Started</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {scans.map((scan) => (
              <TableRow key={scan.id}>
                <TableCell>
                  <Link href={`/health-scan/${scan.id}`} className="hover:underline">
                    {scan.source_label}
                  </Link>
                </TableCell>
                <TableCell>
                  <Badge variant={statusTone[scan.status] === "danger" ? "destructive" : "secondary"}>
                    {scan.status.replace("_", " ")}
                  </Badge>
                </TableCell>
                <TableCell>{scan.summary?.agent_count ?? "—"}</TableCell>
                <TableCell>{new Date(scan.created_at).toLocaleString()}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </div>
  );
}
