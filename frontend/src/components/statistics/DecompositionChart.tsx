import { useState } from "react";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { DecompositionPoint } from "@/api/types";
import { ChartTooltip } from "@/components/charts/ChartTooltip";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { formatCount, formatMonth } from "@/lib/format";

interface Props {
  points: DecompositionPoint[];
}

type Layer = "trend" | "seasonal" | "resid";

const LAYER_LABELS: Record<Layer, string> = {
  trend: "Тренд",
  seasonal: "Сезонність",
  resid: "Залишки",
};

const LAYER_COLORS: Record<Layer, string> = {
  trend: "hsl(25 95% 53%)",
  seasonal: "hsl(142 76% 36%)",
  resid: "hsl(var(--muted-foreground))",
};

export function DecompositionChart({ points }: Props) {
  const [activeLayers, setActiveLayers] = useState<Set<Layer>>(
    new Set(["trend"]),
  );

  const hasDecomposition = points.some((p) => p.trend !== null);

  const data = points.map((p) => ({
    label: formatMonth(p.period),
    observed: p.observed,
    trend: p.trend,
    seasonal: p.seasonal,
    resid: p.resid,
  }));

  function toggle(layer: Layer) {
    setActiveLayers((prev) => {
      const next = new Set(prev);
      if (next.has(layer)) {
        next.delete(layer);
      } else {
        next.add(layer);
      }
      return next;
    });
  }

  return (
    <Card className="p-6">
      <CardHeader className="p-0 pb-4">
        <div className="flex items-start justify-between gap-4">
          <div>
            <CardTitle className="text-base">
              Декомпозиція часового ряду
            </CardTitle>
            <CardDescription>
              {hasDecomposition
                ? "Адитивна декомпозиція: тренд + сезонність + залишки"
                : "Недостатньо даних для декомпозиції (потрібно ≥ 24 місяці)"}
            </CardDescription>
          </div>
          {hasDecomposition && (
            <div className="flex shrink-0 gap-1">
              {(["trend", "seasonal", "resid"] as Layer[]).map((layer) => (
                <Button
                  key={layer}
                  variant={activeLayers.has(layer) ? "default" : "outline"}
                  size="sm"
                  className="h-7 px-2 text-xs"
                  onClick={() => toggle(layer)}
                >
                  {LAYER_LABELS[layer]}
                </Button>
              ))}
            </div>
          )}
        </div>
      </CardHeader>
      {data.length === 0 ? (
        <p className="py-12 text-center text-sm text-muted-foreground">
          Поки що немає даних.
        </p>
      ) : (
        <ResponsiveContainer width="100%" height={300}>
          <LineChart
            data={data}
            margin={{ top: 8, right: 16, bottom: 8, left: 8 }}
          >
            <CartesianGrid
              strokeDasharray="3 3"
              stroke="hsl(var(--border))"
            />
            <XAxis
              dataKey="label"
              tick={{ fontSize: 11 }}
              stroke="hsl(var(--muted-foreground))"
            />
            <YAxis
              tick={{ fontSize: 11 }}
              stroke="hsl(var(--muted-foreground))"
              tickFormatter={(n) => formatCount(Number(n))}
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
            <Legend
              wrapperStyle={{ fontSize: 12 }}
              iconType="line"
            />
            <Line
              type="monotone"
              dataKey="observed"
              name="Факт"
              stroke="hsl(var(--primary))"
              strokeWidth={2}
              dot={false}
            />
            {hasDecomposition &&
              (["trend", "seasonal", "resid"] as Layer[]).map((layer) =>
                activeLayers.has(layer) ? (
                  <Line
                    key={layer}
                    type="monotone"
                    dataKey={layer}
                    name={LAYER_LABELS[layer]}
                    stroke={LAYER_COLORS[layer]}
                    strokeWidth={layer === "resid" ? 1 : 2}
                    strokeDasharray={layer === "seasonal" ? "4 2" : undefined}
                    dot={false}
                    connectNulls
                  />
                ) : null,
              )}
          </LineChart>
        </ResponsiveContainer>
      )}
    </Card>
  );
}
