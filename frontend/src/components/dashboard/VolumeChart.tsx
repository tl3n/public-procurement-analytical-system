import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { TimeSeriesPoint } from "@/api/types";
import { ChartTooltip } from "@/components/charts/ChartTooltip";
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

  const total = data.reduce((acc, p) => acc + p.tender_count, 0);

  return (
    <Card className="p-6">
      <CardHeader className="flex flex-row items-start justify-between space-y-0 p-0 pb-4">
        <div>
          <CardTitle className="text-base">Динаміка кількості тендерів</CardTitle>
          <CardDescription>Помісячно</CardDescription>
        </div>
        {data.length > 0 && (
          <div className="text-right">
            <p className="text-[10px] uppercase tracking-wider text-muted-foreground">
              Всього у періоді
            </p>
            <p className="font-mono text-base font-semibold">
              {formatCount(total)}
            </p>
          </div>
        )}
      </CardHeader>
      {data.length === 0 ? (
        <p className="py-12 text-center text-sm text-muted-foreground">
          Поки що немає даних для графіка.
        </p>
      ) : (
        <ResponsiveContainer width="100%" height={280}>
          <AreaChart
            data={data}
            margin={{ top: 8, right: 16, bottom: 8, left: 8 }}
          >
            <defs>
              <linearGradient id="volumeFill" x1="0" y1="0" x2="0" y2="1">
                <stop
                  offset="0%"
                  stopColor="hsl(var(--primary))"
                  stopOpacity={0.28}
                />
                <stop
                  offset="100%"
                  stopColor="hsl(var(--primary))"
                  stopOpacity={0}
                />
              </linearGradient>
            </defs>
            <CartesianGrid
              strokeDasharray="3 3"
              stroke="hsl(var(--border))"
              vertical={false}
            />
            <XAxis
              dataKey="label"
              tick={{ fontSize: 11 }}
              stroke="hsl(var(--muted-foreground))"
              tickLine={false}
              axisLine={false}
            />
            <YAxis
              tick={{ fontSize: 11 }}
              stroke="hsl(var(--muted-foreground))"
              tickLine={false}
              axisLine={false}
              tickFormatter={(n) => formatCount(n)}
              width={48}
            />
            <Tooltip
              cursor={{
                stroke: "hsl(var(--primary))",
                strokeWidth: 1,
                strokeDasharray: "3 3",
              }}
              content={
                <ChartTooltip
                  formatValue={(v) => formatCount(v)}
                />
              }
            />
            <Area
              type="monotone"
              dataKey="tender_count"
              name="Тендери"
              stroke="hsl(var(--primary))"
              strokeWidth={2}
              fill="url(#volumeFill)"
              activeDot={{
                r: 5,
                strokeWidth: 2,
                stroke: "hsl(var(--card))",
              }}
            />
          </AreaChart>
        </ResponsiveContainer>
      )}
    </Card>
  );
}
