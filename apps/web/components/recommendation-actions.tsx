"use client";

import { useTransition } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@agentops/ui";
import { apiFetch } from "@/lib/api-client";

export function RecommendationActions({ id }: { id: string }) {
  const router = useRouter();
  const [isPending, startTransition] = useTransition();

  function setStatus(status: "applied" | "dismissed") {
    startTransition(async () => {
      await apiFetch(`/recommendations/${id}`, {
        method: "PATCH",
        body: JSON.stringify({ status }),
      });
      router.refresh();
    });
  }

  return (
    <div className="flex gap-2">
      <Button size="sm" disabled={isPending} onClick={() => setStatus("applied")}>
        Apply
      </Button>
      <Button size="sm" variant="outline" disabled={isPending} onClick={() => setStatus("dismissed")}>
        Dismiss
      </Button>
    </div>
  );
}
