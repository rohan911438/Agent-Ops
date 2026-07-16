import { cn } from "../lib/utils";

export type StatusPillTone = "success" | "warning" | "danger" | "neutral";

const toneClasses: Record<StatusPillTone, string> = {
  success: "bg-emerald-500/15 text-emerald-500",
  warning: "bg-amber-500/15 text-amber-500",
  danger: "bg-red-500/15 text-red-500",
  neutral: "bg-muted text-muted-foreground",
};

const dotClasses: Record<StatusPillTone, string> = {
  success: "bg-emerald-500",
  warning: "bg-amber-500",
  danger: "bg-red-500",
  neutral: "bg-muted-foreground",
};

export function StatusPill({
  tone = "neutral",
  children,
  className,
}: {
  tone?: StatusPillTone;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium",
        toneClasses[tone],
        className,
      )}
    >
      <span className={cn("h-1.5 w-1.5 rounded-full", dotClasses[tone])} />
      {children}
    </span>
  );
}
