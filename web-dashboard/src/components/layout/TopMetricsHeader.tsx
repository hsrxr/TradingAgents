import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { useDashboardStore } from "@/store/dashboardStore";

const currencyFormatter = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 2,
});

const percentFormatter = new Intl.NumberFormat("en-US", {
  style: "percent",
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
});

export function TopMetricsHeader(): React.JSX.Element {
  const metrics = useDashboardStore((state) => state.baseSnapshot.metrics);
  const isRunning = useDashboardStore((state) => state.isRunning);

  const pnlVariant = metrics.pnl >= 0 ? "default" : "danger";

  return (
    <Card>
      <CardContent className="grid gap-4 pt-4 sm:grid-cols-2 xl:grid-cols-4">
        <MetricItem label="Portfolio Value" value={currencyFormatter.format(metrics.portfolioValue)} />
        <MetricItem
          label="PnL"
          value={currencyFormatter.format(metrics.pnl)}
          accent={
            <Badge variant={pnlVariant}>
              {metrics.pnl >= 0 ? "Profit" : "Drawdown"}
            </Badge>
          }
        />
        <MetricItem label="Risk Exposure" value={percentFormatter.format(metrics.riskExposure)} />
        <MetricItem
          label="System Status"
          value={isRunning ? "RUNNING" : "IDLE"}
          accent={<StatusPill status={isRunning ? "running" : "degraded"} />}
        />
      </CardContent>
    </Card>
  );
}

function StatusPill({ status }: { status: "running" | "degraded" | "halted" }): React.JSX.Element {
  const colorMap: Record<typeof status, string> = {
    running: "bg-emerald-400",
    degraded: "bg-amber-400",
    halted: "bg-rose-400",
  };

  return (
    <span className="inline-flex items-center gap-1.5 text-xs text-zinc-300">
      <span className={`size-2 rounded-full ${colorMap[status]} shadow-[0_0_8px_currentColor]`} />
      live
    </span>
  );
}

function MetricItem({
  label,
  value,
  accent,
}: {
  label: string;
  value: string;
  accent?: React.JSX.Element;
}): React.JSX.Element {
  return (
    <div className="rounded-lg border border-zinc-800 bg-zinc-950/60 px-3 py-2">
      <p className="text-xs uppercase tracking-[0.12em] text-zinc-500">{label}</p>
      <div className="mt-1 flex items-center gap-2">
        <p className="font-mono text-lg text-zinc-100">{value}</p>
        {accent}
      </div>
    </div>
  );
}
