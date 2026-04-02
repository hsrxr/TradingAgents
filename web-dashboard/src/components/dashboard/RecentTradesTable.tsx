import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useDashboardStore } from "@/store/dashboardStore";

export function RecentTradesTable(): React.JSX.Element {
  const trades = useDashboardStore((state) => state.trades);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Recent Executions</CardTitle>
      </CardHeader>
      <CardContent className="overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Time</TableHead>
              <TableHead>Pair</TableHead>
              <TableHead>Side</TableHead>
              <TableHead className="text-right">Qty</TableHead>
              <TableHead className="text-right">Price</TableHead>
              <TableHead>Reason</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {trades.map((trade) => (
              <TableRow key={trade.id}>
                <TableCell className="font-mono text-xs text-zinc-400">
                  {new Date(trade.timestamp).toLocaleTimeString()}
                </TableCell>
                <TableCell>{trade.pair}</TableCell>
                <TableCell>
                  <Badge variant={trade.side === "BUY" ? "default" : "danger"}>{trade.side}</Badge>
                </TableCell>
                <TableCell className="text-right font-mono">{trade.quantity.toFixed(2)}</TableCell>
                <TableCell className="text-right font-mono">${trade.price.toFixed(2)}</TableCell>
                <TableCell className="max-w-80 truncate text-zinc-300">{trade.reason}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}
