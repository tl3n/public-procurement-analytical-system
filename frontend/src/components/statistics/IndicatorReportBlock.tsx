import type { IndicatorReportRow } from "@/api/types";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { formatCount, formatPercent } from "@/lib/format";
import { lookupIndicator } from "@/lib/indicators";

interface Props {
  indicators: IndicatorReportRow[];
}

/** Per-indicator summary cards with a True/False/NULL split bar. */
export function IndicatorReportBlock({ indicators }: Props) {
  return (
    <Card className="p-4">
      <CardHeader className="p-0 pb-3">
        <CardTitle className="text-base">Звіт по індикаторах ризику</CardTitle>
        <CardDescription>
          Розподіл значень True / False / NULL за всіма тендерами
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-3 p-0">
        {indicators.map((row) => (
          <IndicatorRow key={row.code} row={row} />
        ))}
      </CardContent>
    </Card>
  );
}

function IndicatorRow({ row }: { row: IndicatorReportRow }) {
  const meta = lookupIndicator(row.code);
  const total = row.count_total || 1;
  const truePct = (row.count_true / total) * 100;
  const falsePct = (row.count_false / total) * 100;
  const nullPct = (row.count_null / total) * 100;

  return (
    <div className="flex flex-col gap-2 rounded-md border bg-card p-3">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-sm font-medium">{meta.name}</p>
          <p className="text-xs text-muted-foreground">{meta.interpretation}</p>
        </div>
        <p className="whitespace-nowrap text-xs text-muted-foreground">
          {formatCount(row.count_total)} записів
        </p>
      </div>

      {row.count_total === 0 ? (
        <p className="text-xs italic text-muted-foreground">
          Індикатор ще не обчислювався — викличте{" "}
          <code className="rounded bg-muted px-1 py-0.5">POST /admin/recompute</code>.
        </p>
      ) : (
        <>
          <div className="flex h-3 overflow-hidden rounded bg-muted">
            <div
              className="bg-red-500"
              style={{ width: `${truePct}%` }}
              title={`True: ${formatCount(row.count_true)}`}
            />
            <div
              className="bg-green-500"
              style={{ width: `${falsePct}%` }}
              title={`False: ${formatCount(row.count_false)}`}
            />
            <div
              className="bg-muted-foreground/30"
              style={{ width: `${nullPct}%` }}
              title={`NULL: ${formatCount(row.count_null)}`}
            />
          </div>
          <div className="flex justify-between text-xs text-muted-foreground">
            <span>
              <span className="mr-1 inline-block h-2 w-2 rounded-full bg-red-500" />
              True: {formatCount(row.count_true)} ({formatPercent(row.count_true / total)})
            </span>
            <span>
              <span className="mr-1 inline-block h-2 w-2 rounded-full bg-green-500" />
              False: {formatCount(row.count_false)} ({formatPercent(row.count_false / total)})
            </span>
            <span>
              <span className="mr-1 inline-block h-2 w-2 rounded-full bg-muted-foreground/30" />
              NULL: {formatCount(row.count_null)} ({formatPercent(row.count_null / total)})
            </span>
          </div>
          {row.value_type === "numeric" && row.avg_numeric !== null && (
            <p className="text-xs text-muted-foreground">
              Середнє значення: {row.avg_numeric.toFixed(3)}
            </p>
          )}
        </>
      )}
    </div>
  );
}
