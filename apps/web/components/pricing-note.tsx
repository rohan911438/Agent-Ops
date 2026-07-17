import type { ServicePrice } from "@agentops/shared-types";
import { serverApiFetch } from "@/lib/server-api";

const FALLBACK_NOTE = "Future enterprise plans may introduce paid services.";

/** Reads real pricing metadata from the backend (which itself may read
 * on-chain — see docs/FutureMonetization.md) but never blocks the page:
 * any fetch failure just falls back to the static FREE copy below. */
export async function PricingNote() {
  let allFree = true;
  let note = FALLBACK_NOTE;

  try {
    const prices = await serverApiFetch<ServicePrice[]>("/pricing");
    allFree = prices.every((price) => price.price === 0);
    note = prices[0]?.note ?? FALLBACK_NOTE;
  } catch {
    // Pricing display is never load-bearing — keep the static FREE default.
  }

  if (!allFree) return null;

  return (
    <p className="text-xs text-muted-foreground">
      Current Price: <span className="font-medium text-foreground">FREE</span> — {note}
    </p>
  );
}
