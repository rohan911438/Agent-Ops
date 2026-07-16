import { Badge, Card, CardContent } from "@agentops/ui";
import type { ActivityEvent } from "@agentops/shared-types";
import { serverApiFetch } from "@/lib/server-api";
import { ActivitySearch } from "@/components/activity-search";

export default async function ActivityPage({
  searchParams,
}: {
  searchParams: Promise<{ search?: string }>;
}) {
  const { search } = await searchParams;
  const query = search ? `?search=${encodeURIComponent(search)}` : "";
  const events = await serverApiFetch<ActivityEvent[]>(`/activity${query}`);

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Activity</h1>
          <p className="mt-1 text-sm text-muted-foreground">Everything, searchable.</p>
        </div>
        <ActivitySearch />
      </div>

      <Card>
        <CardContent className="pt-6">
          {events.length === 0 ? (
            <p className="text-sm text-muted-foreground">No activity found.</p>
          ) : (
            <ul className="flex flex-col divide-y divide-border">
              {events.map((event) => (
                <li key={event.id} className="flex items-start justify-between gap-4 py-3 text-sm">
                  <div className="flex flex-col gap-1">
                    <div>
                      <span className="font-medium">{event.actor}</span>{" "}
                      <span className="text-muted-foreground">{event.description}</span>
                    </div>
                    <Badge variant="secondary" className="w-fit">
                      {event.event_type}
                    </Badge>
                  </div>
                  <span className="shrink-0 text-xs text-muted-foreground">
                    {new Date(event.created_at).toLocaleString()}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
