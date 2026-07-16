import { Card, CardContent, Skeleton } from "@agentops/ui";

export default function ActivityLoading() {
  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <Skeleton className="h-7 w-28" />
          <Skeleton className="mt-2 h-4 w-48" />
        </div>
        <Skeleton className="h-9 w-56" />
      </div>

      <Card>
        <CardContent className="flex flex-col divide-y divide-border pt-6">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="flex items-center justify-between gap-4 py-3">
              <Skeleton className="h-4 w-64" />
              <Skeleton className="h-3 w-20" />
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
