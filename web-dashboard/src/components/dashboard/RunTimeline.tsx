import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useDashboardStore } from "@/store/dashboardStore";

const eventStyleMap: Record<string, string> = {
  run_started: "text-emerald-300 border-emerald-500/40",
  node_start: "text-cyan-300 border-cyan-500/40",
  llm_call: "text-violet-300 border-violet-500/40",
  llm_token: "text-indigo-300 border-indigo-500/40",
  tool_start: "text-amber-300 border-amber-500/40",
  tool_end: "text-yellow-300 border-yellow-500/40",
  tool_call: "text-amber-300 border-amber-500/40",
  node_end: "text-sky-300 border-sky-500/40",
  run_completed: "text-green-300 border-green-500/40",
  error: "text-rose-300 border-rose-500/40",
};

export function RunTimeline(): React.JSX.Element {
  const events = useDashboardStore((state) => state.runtimeEvents);

  return (
    <Card className="h-full">
      <CardHeader>
        <CardTitle>Run Timeline</CardTitle>
      </CardHeader>
      <CardContent className="h-[420px]">
        <ScrollArea className="h-full">
          <ol className="space-y-3">
            {events.map((event) => (
              <li key={event.id} className="rounded-md border border-zinc-800 bg-zinc-950/80 p-3">
                <div className="mb-1 flex items-center justify-between gap-2">
                  <span
                    className={`rounded-full border px-2 py-0.5 text-[10px] uppercase tracking-[0.1em] ${
                      eventStyleMap[event.event] ?? "text-zinc-300 border-zinc-600"
                    }`}
                  >
                    {event.event.replaceAll("_", " ")}
                  </span>
                  <span className="font-mono text-[11px] text-zinc-500">
                    {new Date(event.timestamp).toLocaleTimeString()}
                  </span>
                </div>
                <p className="text-xs uppercase tracking-[0.08em] text-zinc-400">{event.actor}</p>
                <p className="mt-1 text-sm text-zinc-200">{event.detail}</p>
              </li>
            ))}
          </ol>
        </ScrollArea>
      </CardContent>
    </Card>
  );
}
