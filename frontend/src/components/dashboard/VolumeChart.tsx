import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { TimeSeriesPoint } from "@/api/types";
import {
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { formatCount, formatMonth } from "@/lib/format";

interface Props {
  points: TimeSeriesPoint[];
}

export function VolumeChart({ points }: Props) {
  const data = points.map((p) => ({
    period: p.period,
    label: formatMonth(p.period),
    tender_count: p.tender_count,
  }));

  return (
    <Card className="p-6">
      <CardHeader className="p-0 pb-4">
        <CardTitle className="text-base">Динаміка кількості тендерів</CardTitle>
        <CardDescription>Помісячно</CardDescription>
      </CardHeader>
      {data.length === 0 ? (
        <p className="py-12 text-center text-sm text-muted-foreground">
          Поки що немає даних для графіка.
        </p>
      ) : (
        <ResponsiveContainer width="100%" height={280}>
          <LineChart
            data={data}
            margin={{ top: 8, right: 16, bottom: 8, left: 8 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
            <XAxis
              dataKey="label"
              tick={{ fontSize: 12 }}
              stroke="hsl(var(--muted-foreground))"
            />
            <YAxis
              tick={{ fontSize: 12 }}
              stroke="hsl(var(--muted-foreground))"
              tickFormatter={(n) => formatCount(n)}
            />
            <Tooltip
              labelFormatter={(label) => String(label)}
              formatter={(value) => [formatCount(Number(value)), "тендери"]}
            />
            <Line
              type="monotone"
              dataKey="tender_count"
              stroke="hsl(var(--primary))"
              strokeWidth={2}
              dot={{ r: 3 }}
              activeDot={{ r: 5 }}
            />
          </LineChart>
        </ResponsiveContainer>
      )}
    </Card>
  );
}
