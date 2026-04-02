import * as React from "react";
import { cn } from "@/lib/utils";

const ScrollArea = React.forwardRef<HTMLDivElement, React.ComponentProps<"div">>(function ScrollArea(
  { className, ...props },
  ref,
) {
  return (
    <div
      ref={ref}
      className={cn(
        "overflow-y-auto rounded-md pr-1 scrollbar-thin scrollbar-track-zinc-900 scrollbar-thumb-zinc-700",
        className,
      )}
      {...props}
    />
  );
});

export { ScrollArea };
