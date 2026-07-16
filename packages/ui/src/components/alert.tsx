import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "../lib/utils";

const alertVariants = cva("relative w-full rounded-lg border p-4 text-sm transition-colors", {
  variants: {
    variant: {
      default: "border-border bg-card text-card-foreground",
      warning: "border-zinc-800 bg-zinc-950 text-zinc-300",
      destructive: "border-white bg-zinc-950 text-white font-medium",
    },
  },
  defaultVariants: { variant: "default" },
});

export interface AlertProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof alertVariants> {}

export function Alert({ className, variant, ...props }: AlertProps) {
  return <div role="alert" className={cn(alertVariants({ variant }), className)} {...props} />;
}

export function AlertTitle({ className, ...props }: React.HTMLAttributes<HTMLHeadingElement>) {
  return <h5 className={cn("mb-1 font-medium leading-none", className)} {...props} />;
}

export function AlertDescription({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("text-sm opacity-90", className)} {...props} />;
}
