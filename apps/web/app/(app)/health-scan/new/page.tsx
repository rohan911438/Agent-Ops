import { DataSourcePicker } from "@/components/health-scan/data-source-picker";

export default function NewHealthScanPage() {
  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Choose a Data Source</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Upload a manifest or connect a repository to start a Health Scan.
        </p>
      </div>
      <DataSourcePicker />
    </div>
  );
}
