import { Link } from "@tanstack/react-router";

import type { TenderSummary } from "@/api/types";
import {
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { formatMoney } from "@/lib/format";

interface Props {
  tenders: TenderSummary[];
}

export function TopRiskTenders({ tenders }: Props) {
  return (
    <Card className="p-6">
      <CardHeader className="p-0 pb-4">
        <CardTitle className="text-base">
          Тендери з найвищим ризиком
        </CardTitle>
        <CardDescription>
          За кількістю спрацьованих булевих індикаторів
        </CardDescription>
      </CardHeader>
      {tenders.length === 0 ? (
        <p className="py-6 text-sm text-muted-foreground">
          Поки що немає тендерів зі спрацьованими індикаторами. Запустіть{" "}
          <code className="rounded bg-muted px-1 py-0.5 text-xs">
            POST /admin/recompute
          </code>{" "}
          щоб обчислити значення для зібраних даних.
        </p>
      ) : (
        <ul className="divide-y">
          {tenders.map((t) => (
            <li key={t.id} className="py-3">
              <Link
                to="/tenders/$id"
                params={{ id: t.id }}
                className="flex items-center justify-between gap-4 hover:underline"
              >
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium">
                    {t.title ?? t.tender_id_human ?? t.id}
                  </p>
                  <p className="truncate text-xs text-muted-foreground">
                    {t.buyer_name ?? "—"}
                  </p>
                </div>
                <div className="whitespace-nowrap text-xs text-muted-foreground">
                  {formatMoney(t.value_amount, t.value_currency ?? "грн")}
                </div>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}
