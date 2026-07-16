import { cn } from "../lib/utils";

export type StepState = "complete" | "active" | "pending" | "error";

export interface StepperStep {
  label: string;
  description?: string;
  state: StepState;
}

const circleClasses: Record<StepState, string> = {
  complete: "bg-white text-black border border-white",
  active: "bg-zinc-800 text-white border border-zinc-700 font-medium",
  pending: "bg-zinc-950 text-zinc-600 border border-zinc-900",
  error: "bg-black text-white border border-white border-dashed font-bold",
};

const connectorClasses: Record<StepState, string> = {
  complete: "bg-white",
  active: "bg-zinc-800",
  pending: "bg-zinc-900",
  error: "bg-zinc-900",
};

const labelClasses: Record<StepState, string> = {
  complete: "text-zinc-200",
  active: "text-white font-medium",
  pending: "text-zinc-600",
  error: "text-white font-medium underline decoration-zinc-500",
};

function StepIcon({ state, index }: { state: StepState; index: number }) {
  if (state === "complete") {
    return (
      <svg viewBox="0 0 20 20" fill="currentColor" className="h-3.5 w-3.5">
        <path
          fillRule="evenodd"
          d="M16.7 5.3a1 1 0 010 1.4l-7.5 7.5a1 1 0 01-1.4 0l-3.5-3.5a1 1 0 111.4-1.4l2.8 2.8 6.8-6.8a1 1 0 011.4 0z"
          clipRule="evenodd"
        />
      </svg>
    );
  }
  if (state === "error") {
    return (
      <svg viewBox="0 0 20 20" fill="currentColor" className="h-3.5 w-3.5">
        <path
          fillRule="evenodd"
          d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.7 7.3a1 1 0 011.4 0l0 0 1.4 1.4 1.4-1.4a1 1 0 111.4 1.4L12.9 10l1.4 1.4a1 1 0 01-1.4 1.4L11.5 11.4l-1.4 1.4a1 1 0 01-1.4-1.4l1.4-1.4-1.4-1.4a1 1 0 010-1.3z"
          clipRule="evenodd"
        />
      </svg>
    );
  }
  return <span>{index + 1}</span>;
}

export function Stepper({ steps, className }: { steps: StepperStep[]; className?: string }) {
  return (
    <ol className={cn("flex flex-col gap-0", className)}>
      {steps.map((step, i) => (
        <li key={step.label} className="flex gap-3">
          <div className="flex flex-col items-center">
            <span
              className={cn(
                "flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs font-medium transition-colors",
                circleClasses[step.state],
                step.state === "active" && "animate-pulse",
              )}
            >
              <StepIcon state={step.state} index={i} />
            </span>
            {i < steps.length - 1 && (
              <span className={cn("my-1 w-px flex-1", connectorClasses[step.state])} />
            )}
          </div>
          <div className={cn("pb-6", i === steps.length - 1 && "pb-0")}>
            <div className={cn("text-sm", labelClasses[step.state])}>{step.label}</div>
            {step.description && (
              <div className="mt-0.5 text-xs text-muted-foreground">{step.description}</div>
            )}
          </div>
        </li>
      ))}
    </ol>
  );
}
