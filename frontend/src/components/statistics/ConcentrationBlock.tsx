import type { ConcentrationBucketOut } from "@/api/types";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { formatMoney } from "@/lib/format";

interface Props {
  rows: ConcentrationBucketOut[];
}

export function ConcentrationBlock({ rows }: Props) {
  return (
    <Card className="p-4">
      <CardHeader className="p-0 pb-3">
        <CardTitle className="text-base">Концентрація ринку за CPV</CardTitle>
        <CardDescription>
          HHI та Gini по розподілу договірних сум між постачальниками. HHI
          близький до 1 — ринок монополізований.
        </CardDescription>
      </CardHeader>
      <CardContent className="p-0">
        {rows.length === 0 ? (
          <p className="py-8 text-center text-sm text-muted-foreground">
            Даних немає — перевірте наявність підписаних договорів.
          </p>
        ) : (
          <div className="flex flex-col gap-2">
            {rows.map((row) => (
              <ConcentrationRow key={row.cpv} row={row} />
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function ConcentrationRow({ row }: { row: ConcentrationBucketOut }) {
  const hhi = row.hhi;
  const hhiPct = Math.round(hhi * 100);
  const barColor =
    hhi >= 0.5
      ? "bg-red-500"
      : hhi >= 0.25
        ? "bg-amber-400"
        : "bg-green-500";

  return (
    <div className="rounded-md border bg-card p-3">
      <div className="flex items-center justify-between gap-4 text-sm">
        <span className="font-mono font-medium">{row.cpv}</span>
        <span className="whitespace-nowrap text-xs text-muted-foreground">
          {row.supplier_count} постач. · {formatMoney(row.total_value)}
        </span>
      </div>
      <div className="mt-2 flex items-center gap-3">
        <div className="h-2 flex-1 overflow-hidden rounded bg-muted">
          <div className={`h-full ${barColor}`} style={{ width: `${hhiPct}%` }} />
        </div>
        <div className="flex w-36 shrink-0 justify-between text-xs text-muted-foreground">
          <span>
            HHI <span className="font-medium text-foreground">{hhi.toFixed(3)}</span>
          </span>
          <span>
            Gini <span className="font-medium text-foreground">{row.gini.toFixed(3)}</span>
          </span>
        </div>
      </div>
    </div>
  );
}
