import * as React from "react";
import { cn } from "@/lib/utils";

function Separator({ className, ...props }: React.ComponentProps<"div">): React.JSX.Element {
  return <div role="separator" className={cn("h-px w-full bg-zinc-800", className)} {...props} />;
}

export { Separator };
