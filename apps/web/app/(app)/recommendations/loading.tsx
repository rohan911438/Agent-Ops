import { Card, CardContent, CardHeader, Skeleton } from "@agentops/ui";

export default function RecommendationsLoading() {
  return (
    <div className="flex flex-col gap-8">
      <div>
        <Skeleton className="h-7 w-48" />
        <Skeleton className="mt-2 h-4 w-72" />
      </div>

      <div className="flex flex-col gap-3">
        <Skeleton className="h-4 w-40" />
        <div className="grid gap-4 sm:grid-cols-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <Card key={i}>
              <CardHeader>
                <Skeleton className="h-4 w-3/4" />
              </CardHeader>
              <CardContent className="flex flex-col gap-3">
                <Skeleton className="h-3 w-full" />
                <Skeleton className="h-3 w-2/3" />
                <Skeleton className="h-7 w-24" />
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </div>
  );
}
