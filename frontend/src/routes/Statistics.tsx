import { useState } from "react";

import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { api } from "@/api/client";
import { DistributionsBlock } from "@/components/statistics/DistributionsBlock";
import { ExportButtons } from "@/components/statistics/ExportButtons";
import { IndicatorReportBlock } from "@/components/statistics/IndicatorReportBlock";
import { RankingsBlock } from "@/components/statistics/RankingsBlock";
import {
  TimeRangeControls,
  type TimeRange,
} from "@/components/statistics/TimeRangeControls";
import { Card, CardContent } from "@/components/ui/card";

export function Statistics() {
  const [range, setRange] = useState<TimeRange>({});

  const rankings = useQuery({
    queryKey: ["rankings", range],
    queryFn: () => api.getRankings({ ...range, limit: 10 }),
    placeholderData: keepPreviousData,
  });
  const distributions = useQuery({
    queryKey: ["distributions", range],
    queryFn: () => api.getDistributions(range),
    placeholderData: keepPreviousData,
  });
  const indicators = useQuery({
    queryKey: ["indicators"],
    queryFn: api.getIndicatorReport,
  });

  return (
    <div className="flex flex-col gap-6">
      <TimeRangeControls value={range} onChange={setRange} />

      <Section title="Рейтинги" query={rankings}>
        {(data) => (
          <RankingsBlock buyers={data.buyers} suppliers={data.suppliers} />
        )}
      </Section>

      <Section title="Розподіли" query={distributions}>
        {(data) => (
          <DistributionsBlock byCpv={data.by_cpv} byRegion={data.by_region} />
        )}
      </Section>

      <Section title="Індикатори ризику" query={indicators}>
        {(data) => <IndicatorReportBlock indicators={data.indicators} />}
      </Section>

      <ExportButtons range={range} />
    </div>
  );
}

interface SectionProps<T> {
  title: string;
  query: {
    data: T | undefined;
    isPending: boolean;
    isError: boolean;
    error: unknown;
  };
  children: (data: T) => React.ReactNode;
}

function Section<T>({ title, query, children }: SectionProps<T>) {
  if (query.isPending) {
    return <Card className="h-48 animate-pulse bg-muted" aria-label={title} />;
  }
  if (query.isError) {
    return (
      <Card>
        <CardContent className="py-6 text-center">
          <p className="text-sm font-medium">
            Не вдалось завантажити {title.toLowerCase()}.
          </p>
          <p className="mt-1 text-xs text-muted-foreground">
            {(query.error as Error).message}
          </p>
        </CardContent>
      </Card>
    );
  }
  return <>{children(query.data as T)}</>;
}
