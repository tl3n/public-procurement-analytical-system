import { Link } from "@tanstack/react-router";

import type { DistributionBucketOut } from "@/api/types";
import {
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { formatCount, formatMoney } from "@/lib/format";
import { labelForType } from "@/lib/labels";

interface Props {
  distribution: DistributionBucketOut[];
}

/** Renders the type distribution as a horizontal "data bar" list, each row
 *  linking to a pre-filtered tender list. A native list is easier to scan
 *  than a Recharts bar chart for a small, labelled set of categories. */
export function TypeDistributionChart({ distribution }: Props) {
  const maxCount = Math.max(...distribution.map((b) => b.tender_count), 1);

  return (
    <Card className="p-6">
      <CardHeader className="p-0 pb-4">
        <CardTitle className="text-base">Розподіл за типом процедури</CardTitle>
        <CardDescription>Натисніть, щоб відфільтрувати список</CardDescription>
      </CardHeader>
      {distribution.length === 0 ? (
        <p className="py-12 text-center text-sm text-muted-foreground">
          Дані поки відсутні.
        </p>
      ) : (
        <ul className="flex flex-col gap-2">
          {distribution.map((b) => {
            const pct = (b.tender_count / maxCount) * 100;
            return (
              <li key={b.label}>
                <Link
                  to="/tenders"
                  search={{ procurement_method_type: b.label } as never}
                  className="block rounded-md p-2 hover:bg-muted"
                >
                  <div className="flex items-center justify-between gap-3 text-sm">
                    <span className="min-w-0 truncate font-medium">
                      {labelForType(b.label)}
                    </span>
                    <span className="shrink-0 text-muted-foreground">
                      {formatCount(b.tender_count)}
                      {" · "}
                      {formatMoney(b.total_value)}
                    </span>
                  </div>
                  <div className="mt-1 h-2 overflow-hidden rounded bg-muted">
                    <div
                      className="h-full bg-primary"
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </Link>
              </li>
            );
          })}
        </ul>
      )}
    </Card>
  );
}
