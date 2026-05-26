import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { DistributionBucketOut } from "@/api/types";
import { ChartTooltip } from "@/components/charts/ChartTooltip";
import {
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { formatCount } from "@/lib/format";

interface Props {
  byCpv: DistributionBucketOut[];
  byRegion: DistributionBucketOut[];
}

export function DistributionsBlock({ byCpv, byRegion }: Props) {
  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
      <DistributionCard
        title="Розподіл за CPV"
        description="Топ кодів класифікатора"
        data={byCpv}
        labelWidth={130}
      />
      <DistributionCard
        title="Розподіл за регіоном замовника"
        description="За кількістю тендерів"
        data={byRegion}
        labelWidth={200}
      />
    </div>
  );
}

interface DistributionCardProps {
  title: string;
  description: string;
  data: DistributionBucketOut[];
  labelWidth: number;
}

function DistributionCard({
  title,
  description,
  data,
  labelWidth,
}: DistributionCardProps) {
  return (
    <Card className="p-4">
      <CardHeader className="p-0 pb-3">
        <CardTitle className="text-base">{title}</CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      {data.length === 0 ? (
        <p className="py-12 text-center text-sm text-muted-foreground">
          Дані відсутні.
        </p>
      ) : (
        <ResponsiveContainer width="100%" height={Math.max(240, data.length * 28)}>
          <BarChart
            data={data}
            layout="vertical"
            margin={{ top: 4, right: 16, bottom: 4, left: 4 }}
          >
            <CartesianGrid
              strokeDasharray="3 3"
              stroke="hsl(var(--border))"
              horizontal={false}
            />
            <XAxis
              type="number"
              tick={{ fontSize: 11 }}
              stroke="hsl(var(--muted-foreground))"
              tickFormatter={(n) => formatCount(n)}
            />
            <YAxis
              type="category"
              dataKey="label"
              width={labelWidth}
              tick={{ fontSize: 11 }}
              stroke="hsl(var(--muted-foreground))"
            />
            <Tooltip
              cursor={{ fill: "hsl(var(--primary) / 0.06)" }}
              content={
                <ChartTooltip
                  formatValue={(v) => formatCount(v)}
                />
              }
            />
            <Bar
              dataKey="tender_count"
              name="Тендери"
              fill="hsl(var(--primary))"
              radius={[0, 4, 4, 0]}
            />
          </BarChart>
        </ResponsiveContainer>
      )}
    </Card>
  );
}
