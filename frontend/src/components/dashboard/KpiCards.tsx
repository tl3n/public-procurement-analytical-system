import { Link } from "@tanstack/react-router";

import type { DashboardKpis, HighRiskShareOut } from "@/api/types";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { formatCount, formatMoney, formatPercent } from "@/lib/format";

interface Props {
  kpis: DashboardKpis;
  highRiskShare: HighRiskShareOut;
}

export function KpiCards({ kpis, highRiskShare }: Props) {
  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
      <KpiCard
        title="Усього тендерів"
        value={formatCount(kpis.total_tenders)}
        description="У базі системи"
        linkTo="/tenders"
        linkLabel="переглянути всі"
      />
      <KpiCard
        title="Сумарна вартість"
        value={formatMoney(kpis.total_value)}
        description="Очікувана вартість, усі процедури"
        linkTo="/statistics"
        linkLabel="рейтинги"
      />
      <KpiCard
        title="Активні процедури"
        value={formatCount(kpis.active_tenders)}
        description="Статус active.*"
        linkTo="/tenders"
        linkLabel="переглянути"
      />
      <KpiCard
        title="Частка ризикових"
        value={formatPercent(highRiskShare.share)}
        description={`${formatCount(highRiskShare.high_risk_tenders)} із ${formatCount(highRiskShare.total_tenders)}`}
        linkTo="/statistics"
        linkLabel="індикатори"
      />
    </div>
  );
}

interface CardProps {
  title: string;
  value: string;
  description: string;
  linkTo: string;
  linkLabel: string;
}

function KpiCard({ title, value, description, linkTo, linkLabel }: CardProps) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardDescription>{title}</CardDescription>
        <CardTitle className="text-3xl">{value}</CardTitle>
      </CardHeader>
      <CardContent className="flex items-center justify-between text-xs text-muted-foreground">
        <span>{description}</span>
        <Link
          to={linkTo}
          className="font-medium text-foreground hover:underline"
        >
          {linkLabel} →
        </Link>
      </CardContent>
    </Card>
  );
}
