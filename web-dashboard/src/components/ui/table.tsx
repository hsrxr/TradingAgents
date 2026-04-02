import * as React from "react";
import { cn } from "@/lib/utils";

function Table({ className, ...props }: React.ComponentProps<"table">): React.JSX.Element {
  return <table className={cn("w-full text-sm", className)} {...props} />;
}

function TableHeader({ className, ...props }: React.ComponentProps<"thead">): React.JSX.Element {
  return <thead className={cn("text-xs uppercase tracking-wider text-zinc-400", className)} {...props} />;
}

function TableBody({ className, ...props }: React.ComponentProps<"tbody">): React.JSX.Element {
  return <tbody className={cn("divide-y divide-zinc-800", className)} {...props} />;
}

function TableRow({ className, ...props }: React.ComponentProps<"tr">): React.JSX.Element {
  return <tr className={cn("hover:bg-zinc-900/70", className)} {...props} />;
}

function TableHead({ className, ...props }: React.ComponentProps<"th">): React.JSX.Element {
  return <th className={cn("px-3 py-2 text-left font-medium", className)} {...props} />;
}

function TableCell({ className, ...props }: React.ComponentProps<"td">): React.JSX.Element {
  return <td className={cn("px-3 py-2 text-zinc-200", className)} {...props} />;
}

export { Table, TableHeader, TableBody, TableRow, TableHead, TableCell };
