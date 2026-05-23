import { useQuery } from "@tanstack/react-query";

import { api } from "@/api/client";
import { KpiCards } from "@/components/dashboard/KpiCards";
import { TopRiskTenders } from "@/components/dashboard/TopRiskTenders";
import { TypeDistributionChart } from "@/components/dashboard/TypeDistributionChart";
import { VolumeChart } from "@/components/dashboard/VolumeChart";
import { Card, CardContent } from "@/components/ui/card";

export function Dashboard() {
  const { data, isPending, isError, error } = useQuery({
    queryKey: ["dashboard"],
    queryFn: api.getDashboard,
  });

  if (isPending) {
    return <DashboardSkeleton />;
  }
  if (isError) {
    return <DashboardError message={(error as Error).message} />;
  }
  return (
    <div className="flex flex-col gap-6">
      <KpiCards kpis={data.kpis} highRiskShare={data.high_risk_share} />
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <VolumeChart points={data.volume_over_time} />
        <TypeDistributionChart
          distribution={data.procurement_type_distribution}
        />
      </div>
      <TopRiskTenders tenders={data.top_risk_tenders} />
    </div>
  );
}

function DashboardSkeleton() {
  return (
    <div className="flex flex-col gap-6">
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Card key={i} className="h-28 animate-pulse bg-muted" />
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
