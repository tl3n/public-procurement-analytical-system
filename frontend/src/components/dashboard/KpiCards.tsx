import { Link } from "@tanstack/react-router";
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  FileSearch,
  Wallet,
  type LucideIcon,
} from "lucide-react";

import type { DashboardKpis, HighRiskShareOut } from "@/api/types";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { formatCount, formatMoney, formatPercent } from "@/lib/format";
import { cn } from "@/lib/utils";

interface Props {
  kpis: DashboardKpis;
  highRiskShare: HighRiskShareOut;
}

export function KpiCards({ kpis, highRiskShare }: Props) {
  // Color-code the risk-share card by severity — anything past 30% gets a
  // warning tint, past 60% a danger tint, so the most alarming KPI doesn't
  // sit in the same neutral box as "total tenders".
  const riskTone =
    highRiskShare.share >= 0.6
      ? "danger"
      : highRiskShare.share >= 0.3
        ? "warning"
        : "neutral";

  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
      <KpiCard
        icon={FileSearch}
        title="Усього тендерів"
        value={formatCount(kpis.total_tenders)}
        description="У базі системи"
        linkTo="/tenders"
        linkLabel="переглянути всі"
      />
      <KpiCard
        icon={Wallet}
        title="Сумарна вартість"
        value={formatMoney(kpis.total_value)}
        description="Очікувана вартість, усі процедури"
        linkTo="/statistics"
        linkLabel="рейтинги"
      />
      <KpiCard
        icon={Activity}
        title="Активні процедури"
        value={formatCount(kpis.active_tenders)}
        description="У стані active.*"
        linkTo="/tenders"
        linkLabel="переглянути"
      />
      <KpiCard
        icon={AlertTriangle}
        title="Частка ризикових"
        value={formatPercent(highRiskShare.share)}
        description={`${formatCount(highRiskShare.high_risk_tenders)} із ${formatCount(highRiskShare.total_tenders)}`}
        linkTo="/statistics"
        linkLabel="звіт по індикаторах"
        tone={riskTone}
        barFraction={highRiskShare.share}
      />
    </div>
  );
}

type Tone = "neutral" | "warning" | "danger";

interface CardProps {
  icon: LucideIcon;
  title: string;
  value: string;
  description: string;
  linkTo: string;
  linkLabel: string;
  tone?: Tone;
  /** When supplied, renders a thin horizontal progress bar at card foot. */
  barFraction?: number;
}

const TONE_CLASSES: Record<
  Tone,
  { icon: string; value: string; surface: string; bar: string }
> = {
  neutral: {
    icon: "bg-primary/10 text-primary",
    value: "text-foreground",
    surface: "",
    bar: "bg-primary",
  },
  warning: {
    icon: "bg-amber-100 text-amber-700",
    value: "text-amber-700",
    surface:
      "bg-gradient-to-br from-amber-50/80 via-card to-card ring-1 ring-amber-200/60",
    bar: "bg-amber-500",
  },
  danger: {
    icon: "bg-red-100 text-red-700",
    value: "text-red-700",
    surface:
      "bg-gradient-to-br from-red-50/90 via-card to-card ring-1 ring-red-200/70",
    bar: "bg-red-500",
  },
};

function KpiCard({
  icon: Icon,
  title,
  value,
  description,
  linkTo,
  linkLabel,
  tone = "neutral",
  barFraction,
}: CardProps) {
  const styles = TONE_CLASSES[tone];
  const barPct =
    barFraction != null
      ? Math.min(100, Math.max(0, barFraction * 100))
      : null;

  return (
    <Card
      className={cn(
        "relative overflow-hidden transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md",
        styles.surface,
      )}
    >
      <CardHeader className="flex flex-row items-start justify-between space-y-0 pb-2">
        <CardDescription className="text-[10px] uppercase tracking-[0.14em]">
          {title}
        </CardDescription>
        <span
          className={cn(
            "grid h-9 w-9 place-items-center rounded-lg",
            styles.icon,
          )}
        >
          <Icon className="h-4 w-4" />
        </span>
      </CardHeader>
      <CardContent className="space-y-3">
        <CardTitle
          className={cn(
            "font-mono text-3xl font-bold tracking-tight",
            styles.value,
          )}
        >
          {value}
        </CardTitle>
        {barPct != null && (
          <div
            className="h-1.5 w-full overflow-hidden rounded-full bg-muted"
            aria-hidden
          >
            <div
              className={cn("h-full rounded-full transition-all", styles.bar)}
              style={{ width: `${barPct}%` }}
            />
          </div>
        )}
        <div className="flex items-center justify-between border-t pt-3 text-xs text-muted-foreground">
          <span className="truncate">{description}</span>
          <Link
            to={linkTo}
            className="inline-flex shrink-0 items-center gap-1 font-medium text-primary hover:underline"
          >
            {linkLabel}
            <ArrowRight className="h-3 w-3" />
          </Link>
        </div>
      </CardContent>
    </Card>
  );
}
