import { useQuery, useQueryClient } from "@tanstack/react-query";
import { RefreshCw } from "lucide-react";

import { api } from "@/api/client";
import { KpiCards } from "@/components/dashboard/KpiCards";
import { TopRiskTenders } from "@/components/dashboard/TopRiskTenders";
import { TypeDistributionChart } from "@/components/dashboard/TypeDistributionChart";
import { VolumeChart } from "@/components/dashboard/VolumeChart";
import { PageHeader } from "@/components/layout/PageHeader";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

export function Dashboard() {
  const queryClient = useQueryClient();
  const { data, isPending, isError, error, isFetching, dataUpdatedAt } =
    useQuery({
      queryKey: ["dashboard"],
      queryFn: api.getDashboard,
    });

  const refresh = () =>
    queryClient.invalidateQueries({ queryKey: ["dashboard"] });

  const updated = dataUpdatedAt
    ? new Date(dataUpdatedAt).toLocaleTimeString("uk-UA", {
        hour: "2-digit",
        minute: "2-digit",
      })
    : null;

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Дашборд"
        description="Зведена статистика та найбільш ризикові тендери з бази системи."
        actions={
          <>
            {updated && (
              <span className="text-xs text-muted-foreground">
                Оновлено о {updated}
              </span>
            )}
            <Button
              variant="outline"
              size="sm"
              onClick={refresh}
              disabled={isFetching}
            >
              <RefreshCw
                className={cn(
                  "mr-1.5 h-3.5 w-3.5",
                  isFetching && "animate-spin",
                )}
              />
              Оновити
            </Button>
          </>
        }
      />

      {isPending ? (
        <DashboardSkeleton />
      ) : isError ? (
        <DashboardError message={(error as Error).message} />
      ) : (
        <>
          <KpiCards kpis={data.kpis} highRiskShare={data.high_risk_share} />
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <VolumeChart points={data.volume_over_time} />
            <TypeDistributionChart
              distribution={data.procurement_type_distribution}
            />
          </div>
          <TopRiskTenders tenders={data.top_risk_tenders} />
        </>
      )}
    </div>
  );
}

function DashboardSkeleton() {
  return (
    <div className="flex flex-col gap-6">
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Card key={i} className="p-6">
            <div className="flex justify-between">
              <div className="h-3 w-24 animate-pulse rounded bg-muted" />
              <div className="h-9 w-9 animate-pulse rounded-lg bg-muted" />
            </div>
            <div className="mt-4 h-8 w-32 animate-pulse rounded bg-muted" />
            <div className="mt-4 h-3 w-full animate-pulse rounded bg-muted" />
          </Card>
        ))}
      </div>
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card className="h-72 animate-pulse bg-muted" />
        <Card className="h-72 animate-pulse bg-muted" />
      </div>
      <Card className="h-40 animate-pulse bg-muted" />
    </div>
  );
}

function DashboardError({ message }: { message: string }) {
  return (
    <Card>
      <CardContent className="py-8 text-center">
        <p className="text-sm font-medium text-foreground">
          Не вдалось завантажити дані дашборду.
        </p>
        <p className="mt-2 text-xs text-muted-foreground">{message}</p>
      </CardContent>
    </Card>
  );
}
