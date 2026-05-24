import { Link, useParams } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft } from "lucide-react";

import { api } from "@/api/client";
import { PageHeader } from "@/components/layout/PageHeader";
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

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Деталі тендера"
        description={data?.tender_id_human ?? id}
        actions={
          <Link
            to="/tenders"
            className="inline-flex items-center gap-1.5 rounded-md border bg-card px-3 py-1.5 text-xs font-medium text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            До переліку
          </Link>
        }
      />

      {isPending ? (
        <div className="flex flex-col gap-4">
          <Card className="h-40 animate-pulse bg-muted" />
          <Card className="h-72 animate-pulse bg-muted" />
          <Card className="h-40 animate-pulse bg-muted" />
        </div>
      ) : isError ? (
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
      ) : (
        <>
          <TenderHeader tender={data} />
          <LotsSection lots={data.lots} />
          <ContractsSection contracts={data.contracts} />
          <RiskIndicatorsSection values={data.risk_indicator_values} />
        </>
      )}
    </div>
  );
}
