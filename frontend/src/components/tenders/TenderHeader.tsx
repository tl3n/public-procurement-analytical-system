import type { TenderDetail } from "@/api/types";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { formatMoney } from "@/lib/format";

import { StatusBadge } from "./StatusBadge";

interface Props {
  tender: TenderDetail;
}

export function TenderHeader({ tender }: Props) {
  const prozorroUrl = tender.tender_id_human
    ? `https://prozorro.gov.ua/tender/${encodeURIComponent(tender.tender_id_human)}`
    : null;

  return (
    <Card>
      <CardHeader>
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0 flex-1">
            <CardDescription className="font-mono text-xs">
              {tender.tender_id_human ?? tender.id}
            </CardDescription>
            <CardTitle className="mt-1 text-xl">
              {tender.title ?? "Без назви"}
            </CardTitle>
          </div>
          <div className="flex shrink-0 flex-col items-end gap-2">
            <StatusBadge status={tender.status} />
            {prozorroUrl && (
              <Button asChild variant="outline" size="sm">
                <a href={prozorroUrl} target="_blank" rel="noreferrer">
                  Відкрити на Prozorro ↗
                </a>
              </Button>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent className="grid grid-cols-1 gap-4 text-sm md:grid-cols-2 lg:grid-cols-4">
        <Field
          label="Тип процедури"
          value={tender.procurement_method_type ?? "—"}
        />
        <Field
          label="Очікувана вартість"
          value={formatMoney(tender.value_amount, tender.value_currency ?? "грн")}
        />
        <Field
          label="Дата публікації"
          value={
            tender.date_published
              ? new Date(tender.date_published).toLocaleString("uk-UA")
              : "—"
          }
        />
        <Field
          label="Регіон замовника"
          value={tender.buyer_region ?? "—"}
        />
        <Field
          label="Замовник"
          value={
            <>
              <span>{tender.buyer_name ?? "—"}</span>
              {tender.buyer_edrpou && (
                <span className="ml-1 text-xs text-muted-foreground">
                  ({tender.buyer_edrpou})
                </span>
              )}
            </>
          }
        />
        <Field
          label="Початок прийому"
          value={
            tender.tender_period_start
              ? new Date(tender.tender_period_start).toLocaleString("uk-UA")
              : "—"
          }
        />
        <Field
          label="Кінець прийому"
          value={
            tender.tender_period_end
              ? new Date(tender.tender_period_end).toLocaleString("uk-UA")
              : "—"
          }
        />
        {tender.description && (
          <Field
            label="Опис"
            value={tender.description}
            className="lg:col-span-4"
          />
        )}
      </CardContent>
    </Card>
  );
}

function Field({
  label,
  value,
  className,
}: {
  label: string;
  value: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={className}>
      <p className="text-xs uppercase tracking-wider text-muted-foreground">
        {label}
      </p>
      <p className="mt-1">{value}</p>
    </div>
  );
}
