import { useMemo } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceDot,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useDashboardStore } from "@/store/dashboardStore";

function formatTsLabel(timestamp: string): string {
  const date = new Date(timestamp);
  return `${date.getUTCHours().toString().padStart(2, "0")}:${date
    .getUTCMinutes()
    .toString()
    .padStart(2, "0")}`;
}

export function MarketChart(): React.JSX.Element {
  const { pair, priceSeries, executionMarkers } = useDashboardStore((state) => state.baseSnapshot);

  const markerByTs = useMemo(() => {
    const map = new Map<string, { side: "BUY" | "SELL"; price: number }>();
    executionMarkers.forEach((marker) => {
      map.set(marker.timestamp, { side: marker.side, price: marker.price });
    });
    return map;
  }, [executionMarkers]);

  const chartData = useMemo(
    () =>
      priceSeries.map((point) => {
        const marker = markerByTs.get(point.timestamp);
        return {
          ...point,
          timeLabel: formatTsLabel(point.timestamp),
          markerSide: marker?.side,
          markerPrice: marker?.price,
        };
      }),
    [markerByTs, priceSeries],
  );

  return (
    <Card className="h-full">
      <CardHeader>
        <CardTitle>{pair} Market Tape</CardTitle>
      </CardHeader>
      <CardContent className="h-[360px]">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData} margin={{ top: 8, right: 18, left: 4, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
            <XAxis dataKey="timeLabel" tick={{ fill: "#9ca3af", fontSize: 11 }} tickLine={false} axisLine={false} />
            <YAxis tick={{ fill: "#9ca3af", fontSize: 11 }} domain={["dataMin - 5", "dataMax + 5"]} tickLine={false} axisLine={false} width={56} />
            <Tooltip
              cursor={{ stroke: "#34d399", strokeOpacity: 0.3 }}
              contentStyle={{
                background: "#050b08",
                border: "1px solid #065f46",
                borderRadius: "8px",
                color: "#d4d4d8",
              }}
              formatter={(value) => {
                const numericValue = typeof value === "number" ? value : Number(value ?? 0);
                return [`$${numericValue.toFixed(2)}`, "Price"];
              }}
            />
            <Line
              type="monotone"
              dataKey="price"
              stroke="#34d399"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 5, fill: "#6ee7b7", stroke: "#064e3b", strokeWidth: 1 }}
            />
            {chartData
              .filter((item) => item.markerSide)
              .map((item) => (
                <ReferenceDot
                  key={`${item.timestamp}-${item.markerSide}`}
                  x={item.timeLabel}
                  y={item.markerPrice}
                  r={6}
                  fill={item.markerSide === "BUY" ? "#22c55e" : "#f43f5e"}
                  stroke="none"
                  label={{
                    value: item.markerSide,
                    position: "top",
                    fill: item.markerSide === "BUY" ? "#86efac" : "#fda4af",
                    fontSize: 10,
                    fontWeight: 600,
                  }}
                />
              ))}
          </LineChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
