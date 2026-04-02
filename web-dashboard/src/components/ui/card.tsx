import * as React from "react";
import { cn } from "@/lib/utils";

function Card({ className, ...props }: React.ComponentProps<"div">): React.JSX.Element {
  return (
    <div
      data-slot="card"
      className={cn(
        "rounded-xl border border-emerald-500/20 bg-[#0b1411]/80 text-zinc-100 shadow-[0_0_30px_rgba(17,185,129,0.08)] backdrop-blur",
        className,
      )}
      {...props}
    />
  );
}

function CardHeader({ className, ...props }: React.ComponentProps<"div">): React.JSX.Element {
  return <div data-slot="card-header" className={cn("p-4 pb-2", className)} {...props} />;
}

function CardTitle({ className, ...props }: React.ComponentProps<"h3">): React.JSX.Element {
  return (
    <h3
      data-slot="card-title"
      className={cn("font-semibold tracking-wide text-emerald-300", className)}
      {...props}
    />
  );
}

function CardContent({ className, ...props }: React.ComponentProps<"div">): React.JSX.Element {
  return <div data-slot="card-content" className={cn("p-4 pt-2", className)} {...props} />;
}

export { Card, CardHeader, CardTitle, CardContent };
