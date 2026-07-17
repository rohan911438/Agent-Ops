import type { ReportVerification } from "@agentops/shared-types";
import { apiFetch, ApiError } from "@/lib/api-client";

/** Returns null (not throws) when no verification record exists yet — the
 * verification card simply omits itself, never breaking the report view. */
export async function getReportVerification(scanId: string): Promise<ReportVerification | null> {
  try {
    return await apiFetch<ReportVerification>(`/scans/${scanId}/verification`);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) {
      return null;
    }
    throw error;
  }
}
