import { notFound } from "next/navigation";
import type { HealthScan } from "@agentops/shared-types";
import { ApiError } from "@/lib/api-client";
import { serverApiFetch } from "@/lib/server-api";
import { ScanStatus } from "@/components/health-scan/scan-status";

export default async function HealthScanDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;

  let scan: HealthScan;
  try {
    scan = await serverApiFetch<HealthScan>(`/scans/${id}`);
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) notFound();
    throw err;
  }

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">{scan.source_label}</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          {scan.source_type === "github" ? "GitHub repository scan" : "Uploaded agent manifest"}
        </p>
      </div>
      <ScanStatus initialScan={scan} />
    </div>
  );
}
