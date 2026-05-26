import { ArrowUpRight, Building2, Calendar, MapPin, Tag } from "lucide-react";

import type { TenderDetail } from "@/api/types";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { formatMoney } from "@/lib/format";
import { labelForType } from "@/lib/labels";
import { cn } from "@/lib/utils";

import { StatusBadge } from "./StatusBadge";

interface Props {
  tender: TenderDetail;
}

/** Map a status string to the side-stripe colour. Mirrors StatusBadge's tone
 *  decisions so the stripe carries the same visual cue as the badge. */
function stripeForStatus(status: string | null): string {
  if (!status) return "bg-border";
  if (status === "complete" || status === "active.awarded") return "bg-[hsl(var(--success))]";
  if (status === "cancelled" || status === "unsuccessful")
    return "bg-[hsl(var(--danger))]";
  if (status.startsWith("active.")) return "bg-[hsl(var(--warning))]";
  return "bg-border";
}

export function TenderHeader({ tender }: Props) {
  const prozorroUrl = tender.tender_id_human
    ? `https://prozorro.gov.ua/tender/${encodeURIComponent(tender.tender_id_human)}`
    : null;

  const published = tender.date_published
    ? new Date(tender.date_published).toLocaleString("uk-UA")
    : "—";
  const periodStart = tender.tender_period_start
    ? new Date(tender.tender_period_start).toLocaleString("uk-UA")
    : "—";
  const periodEnd = tender.tender_period_end
    ? new Date(tender.tender_period_end).toLocaleString("uk-UA")
    : "—";

  return (
    <Card className="relative overflow-hidden">
      {/* Status-coloured left stripe to make state visible at a glance. */}
      <span
        aria-hidden
        className={cn(
          "absolute inset-y-0 left-0 w-1",
          stripeForStatus(tender.status),
        )}
      />
      <CardContent className="flex flex-col gap-6 p-6 pl-8">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div className="min-w-0 flex-1 space-y-3">
            <div className="flex flex-wrap items-center gap-2">
              <span className="rounded bg-muted px-1.5 py-0.5 font-mono text-[11px] text-muted-foreground">
                {tender.tender_id_human ?? tender.id}
              </span>
              <StatusBadge status={tender.status} />
              {tender.procurement_method_type && (
                <span className="inline-flex items-center gap-1 text-xs text-muted-foreground">
                  <Tag className="h-3 w-3" />
                  {labelForType(tender.procurement_method_type)}
                </span>
              )}
            </div>
            <h2 className="text-2xl font-bold leading-tight tracking-tight text-foreground">
              {tender.title ?? "Без назви"}
            </h2>
            {tender.description && (
              <p className="max-w-3xl text-sm leading-relaxed text-muted-foreground">
                {tender.description}
              </p>
            )}
          </div>
          <div className="flex shrink-0 flex-col items-stretch gap-3 lg:items-end">
            <div className="rounded-lg border border-border/70 bg-muted/40 p-4 lg:min-w-[220px]">
              <p className="text-[10px] uppercase tracking-[0.14em] text-muted-foreground">
                Очікувана вартість
              </p>
              <p className="mt-1 font-mono text-2xl font-bold tracking-tight">
                {formatMoney(
                  tender.value_amount,
                  tender.value_currency ?? "грн",
                )}
              </p>
            </div>
            {prozorroUrl && (
              <Button asChild variant="outline" size="sm">
                <a href={prozorroUrl} target="_blank" rel="noreferrer">
                  Відкрити на Prozorro
                  <ArrowUpRight className="ml-1 h-3.5 w-3.5" />
                </a>
              </Button>
            )}
          </div>
        </div>

        <dl className="grid grid-cols-1 gap-4 border-t border-border/60 pt-5 text-sm sm:grid-cols-2 lg:grid-cols-4">
          <Meta
            icon={Building2}
            label="Замовник"
            value={
              <>
                <span>{tender.buyer_name ?? "—"}</span>
                {tender.buyer_edrpou && (
                  <span className="ml-1 font-mono text-xs text-muted-foreground">
                    ({tender.buyer_edrpou})
                  </span>
                )}
              </>
            }
          />
          <Meta
            icon={MapPin}
            label="Регіон"
            value={tender.buyer_region ?? "—"}
          />
          <Meta
            icon={Calendar}
            label="Дата публікації"
            value={published}
          />
          <Meta
            icon={Calendar}
            label="Період подання"
            value={
              <span className="text-sm">
                <span className="block">{periodStart}</span>
                <span className="block text-muted-foreground">
                  → {periodEnd}
                </span>
              </span>
            }
          />
        </dl>
      </CardContent>
    </Card>
  );
}

interface MetaProps {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: React.ReactNode;
}

function Meta({ icon: Icon, label, value }: MetaProps) {
  return (
    <div className="flex gap-2.5">
      <Icon className="mt-0.5 h-3.5 w-3.5 shrink-0 text-muted-foreground" />
      <div className="min-w-0 flex-1">
        <dt className="text-[10px] uppercase tracking-[0.14em] text-muted-foreground">
          {label}
        </dt>
        <dd className="mt-0.5 text-sm">{value}</dd>
      </div>
    </div>
  );
}
