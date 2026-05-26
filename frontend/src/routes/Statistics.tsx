import { useEffect, useState } from "react";

import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { api } from "@/api/client";
import { PageHeader } from "@/components/layout/PageHeader";
import { ConcentrationBlock } from "@/components/statistics/ConcentrationBlock";
import { CorrelationBlock } from "@/components/statistics/CorrelationBlock";
import { DecompositionChart } from "@/components/statistics/DecompositionChart";
import { DistributionsBlock } from "@/components/statistics/DistributionsBlock";
import { ExportButtons } from "@/components/statistics/ExportButtons";
import { IndicatorReportBlock } from "@/components/statistics/IndicatorReportBlock";
import { RankingsBlock } from "@/components/statistics/RankingsBlock";
import {
  TimeRangeControls,
  type TimeRange,
} from "@/components/statistics/TimeRangeControls";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

interface SectionDef {
  id: string;
  title: string;
}

const SECTIONS: SectionDef[] = [
  { id: "rankings", title: "Рейтинги" },
  { id: "distributions", title: "Розподіли" },
  { id: "concentration", title: "Концентрація ринку" },
  { id: "decomposition", title: "Декомпозиція ряду" },
  { id: "correlation", title: "Кореляція" },
  { id: "indicators", title: "Індикатори ризику" },
  { id: "export", title: "Експорт" },
];

export function Statistics() {
  const [range, setRange] = useState<TimeRange>({});
  const activeId = useActiveSection(SECTIONS.map((s) => s.id));

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
  const concentration = useQuery({
    queryKey: ["concentration", range],
    queryFn: () => api.getConcentration(range),
    placeholderData: keepPreviousData,
  });
  const decomposition = useQuery({
    queryKey: ["decomposition"],
    queryFn: api.getDecomposition,
  });
  const correlation = useQuery({
    queryKey: ["correlation"],
    queryFn: api.getCorrelation,
  });
  const indicators = useQuery({
    queryKey: ["indicators"],
    queryFn: api.getIndicatorReport,
  });

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Статистика"
        description="Рейтинги замовників і постачальників, розподіли за категоріями та звіт по індикаторах ризику."
      />
      <TimeRangeControls value={range} onChange={setRange} />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1fr_220px]">
        <div className="flex min-w-0 flex-col gap-6">
          <Section id="rankings" title="Рейтинги" query={rankings}>
            {(data) => (
              <RankingsBlock buyers={data.buyers} suppliers={data.suppliers} />
            )}
          </Section>

          <Section id="distributions" title="Розподіли" query={distributions}>
            {(data) => (
              <DistributionsBlock byCpv={data.by_cpv} byRegion={data.by_region} />
            )}
          </Section>

          <Section
            id="concentration"
            title="Концентрація ринку"
            query={concentration}
          >
            {(data) => <ConcentrationBlock rows={data.rows} />}
          </Section>

          <Section
            id="decomposition"
            title="Декомпозиція часового ряду"
            query={decomposition}
          >
            {(data) => <DecompositionChart points={data.points} />}
          </Section>

          <Section id="correlation" title="Кореляція" query={correlation}>
            {(data) => <CorrelationBlock data={data} />}
          </Section>

          <Section
            id="indicators"
            title="Індикатори ризику"
            query={indicators}
          >
            {(data) => <IndicatorReportBlock indicators={data.indicators} />}
          </Section>

          <section id="export" className="scroll-mt-20">
            <ExportButtons range={range} />
          </section>
        </div>

        <aside className="hidden lg:block">
          <nav
            aria-label="Розділи статистики"
            className="sticky top-20 flex flex-col gap-1 rounded-lg border border-border/60 bg-card/60 p-3 backdrop-blur-sm"
          >
            <p className="px-2 pb-1 text-[10px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
              На сторінці
            </p>
            {SECTIONS.map((s) => {
              const active = s.id === activeId;
              return (
                <a
                  key={s.id}
                  href={`#${s.id}`}
                  className={cn(
                    "group relative rounded-md px-3 py-1.5 text-xs font-medium transition-colors",
                    active
                      ? "bg-primary/10 text-primary"
                      : "text-muted-foreground hover:bg-muted hover:text-foreground",
                  )}
                >
                  {active && (
                    <span className="absolute inset-y-1 left-0 w-0.5 rounded-full bg-primary" />
                  )}
                  {s.title}
                </a>
              );
            })}
          </nav>
        </aside>
      </div>
    </div>
  );
}

interface SectionProps<T> {
  id: string;
  title: string;
  query: {
    data: T | undefined;
    isPending: boolean;
    isError: boolean;
    error: unknown;
  };
  children: (data: T) => React.ReactNode;
}

function Section<T>({ id, title, query, children }: SectionProps<T>) {
  if (query.isPending) {
    return (
      <section id={id} className="scroll-mt-20" aria-label={title}>
        <Card className="h-48 animate-pulse bg-muted" />
      </section>
    );
  }
  if (query.isError) {
    return (
      <section id={id} className="scroll-mt-20" aria-label={title}>
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
      </section>
    );
  }
  return (
    <section id={id} className="scroll-mt-20">
      {children(query.data as T)}
    </section>
  );
}

/** Tracks which section is currently in view so the TOC can highlight it. */
function useActiveSection(ids: string[]): string | null {
  const [active, setActive] = useState<string | null>(ids[0] ?? null);

  useEffect(() => {
    if (typeof window === "undefined") return;

    const observer = new IntersectionObserver(
      (entries) => {
        // Pick the entry closest to the top edge that is currently
        // intersecting — gives a stable "what am I reading" answer.
        const visible = entries
          .filter((e) => e.isIntersecting)
          .sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top);
        if (visible[0]) {
          setActive(visible[0].target.id);
        }
      },
      // Trigger when a section crosses the upper third of the viewport.
      { rootMargin: "-20% 0px -60% 0px", threshold: [0, 1] },
    );

    const elements = ids
      .map((id) => document.getElementById(id))
      .filter((el): el is HTMLElement => el !== null);

    elements.forEach((el) => observer.observe(el));
    return () => observer.disconnect();
  }, [ids]);

  return active;
}
