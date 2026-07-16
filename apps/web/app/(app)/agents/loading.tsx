import { Skeleton } from "@agentops/ui";

export default function AgentsLoading() {
  return (
    <div className="flex flex-col gap-6">
      <div>
        <Skeleton className="h-7 w-28" />
        <Skeleton className="mt-2 h-4 w-64" />
      </div>

      <div className="flex flex-col gap-2 rounded-md border border-border">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="flex items-center gap-6 border-b border-border px-4 py-3 last:border-b-0">
            <Skeleton className="h-4 w-40" />
            <Skeleton className="h-4 w-20" />
            <Skeleton className="h-4 w-16" />
            <Skeleton className="h-4 w-16" />
            <Skeleton className="h-4 w-12" />
            <Skeleton className="h-4 w-12" />
          </div>
        ))}
      </div>
    </div>
  );
}
