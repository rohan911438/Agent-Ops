import { Card, CardContent, CardHeader, CardTitle, StatusPill } from "@agentops/ui";
import type { ReportVerification } from "@agentops/shared-types";

function shortValue(value: string, lead = 6, trail = 4) {
  return value.length > lead + trail + 1 ? `${value.slice(0, lead)}…${value.slice(-trail)}` : value;
}

function formatDate(value: string) {
  return new Date(value).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}

/** Only renders once a report's hash has actually been anchored — an
 * unconfigured or failed submission simply omits this card rather than
 * showing an alarming "verification failed" state in an enterprise report. */
export function VerificationCard({ verification }: { verification: ReportVerification | null }) {
  if (!verification || verification.status !== "confirmed" || !verification.tx_hash) {
    return null;
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between gap-2">
          <CardTitle className="text-foreground">Report Integrity</CardTitle>
          <StatusPill tone="success">Verified on Base</StatusPill>
        </div>
      </CardHeader>
      <CardContent className="flex flex-col gap-4 text-sm">
        <p className="text-muted-foreground">
          This report has been sealed with a tamper-proof record — any future edit to its
          contents would no longer match what was verified here.
        </p>
        <div className="flex flex-col gap-2 border-t border-border/60 pt-4">
          <div className="flex items-center justify-between">
            <span className="text-muted-foreground">Verified</span>
            <span>{formatDate(verification.created_at)}</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-muted-foreground">Report Seal</span>
            <span className="font-mono">{shortValue(verification.report_hash)}</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-muted-foreground">Registry Contract</span>
            <span className="font-mono">{shortValue(verification.contract_address)}</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-muted-foreground">Verification Record</span>
            <span className="font-mono">{shortValue(verification.tx_hash)}</span>
          </div>
        </div>
        {verification.explorer_url && (
          <div className="flex justify-end">
            <a
              href={verification.explorer_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm font-medium text-foreground underline underline-offset-4 hover:no-underline"
            >
              View verification record →
            </a>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
