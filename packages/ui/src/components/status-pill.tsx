import { cn } from "../lib/utils";

export type StatusPillTone = "success" | "warning" | "danger" | "neutral";

const toneClasses: Record<StatusPillTone, string> = {
  success: "bg-zinc-900/50 text-zinc-100 border border-zinc-800",
  warning: "bg-zinc-950 text-zinc-400 border border-zinc-800/80",
  danger: "bg-white text-black font-semibold border border-white",
  neutral: "bg-zinc-950 text-zinc-500 border border-zinc-900",
};

const dotClasses: Record<StatusPillTone, string> = {
  success: "bg-zinc-100",
  warning: "bg-zinc-400",
  danger: "bg-black",
  neutral: "bg-zinc-600",
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
        "inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium tracking-tight transition-colors",
        toneClasses[tone],
        className,
      )}
    >
      <span className={cn("h-1.5 w-1.5 rounded-full", dotClasses[tone])} />
      {children}
    </span>
  );
}
