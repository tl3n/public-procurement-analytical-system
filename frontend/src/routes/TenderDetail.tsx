import { useParams } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";

import { api } from "@/api/client";
import { ContractsSection } from "@/components/tenders/ContractsSection";
import { LotsSection } from "@/components/tenders/LotsSection";
import { RiskIndicatorsSection } from "@/components/tenders/RiskIndicatorsSection";
import { TenderHeader } from "@/components/tenders/TenderHeader";
import { Card, CardContent } from "@/components/ui/card";

export function TenderDetail() {
  const { id } = useParams({ from: "/tenders/$id" });
  const { data, isPending, isError, error } = useQuery({
    queryKey: ["tender", id],
    queryFn: () => api.getTender(id),
  });

  if (isPending) {
    return (
      <div className="flex flex-col gap-4">
        <Card className="h-40 animate-pulse bg-muted" />
        <Card className="h-72 animate-pulse bg-muted" />
      </div>
    );
  }
  if (isError) {
    return (
      <Card>
        <CardContent className="py-8 text-center">
          <p className="text-sm font-medium">
            Не вдалось завантажити тендер.
          </p>
          <p className="mt-1 text-xs text-muted-foreground">
            {(error as Error).message}
          </p>
        </CardContent>
      </Card>
    );
  }
  return (
    <div className="flex flex-col gap-6">
      <TenderHeader tender={data} />
      <LotsSection lots={data.lots} />
      <ContractsSection contracts={data.contracts} />
      <RiskIndicatorsSection values={data.risk_indicator_values} />
    </div>
  );
}
