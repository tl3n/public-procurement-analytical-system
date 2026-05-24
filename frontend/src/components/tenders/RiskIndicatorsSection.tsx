import type { RiskIndicatorValueOut } from "@/api/types";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { lookupIndicator } from "@/lib/indicators";

interface Props {
  values: RiskIndicatorValueOut[];
}

export function RiskIndicatorsSection({ values }: Props) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Індикатори ризику</CardTitle>
        {values.length === 0 ? (
          <CardDescription>
            Індикатори ще не обчислені для цього тендеру. Викличте{" "}
            <code className="rounded bg-muted px-1 py-0.5 text-xs">
              POST /admin/recompute
            </code>
            , щоб запустити пакетний перерахунок.
          </CardDescription>
        ) : null}
      </CardHeader>
      {values.length > 0 && (
        <CardContent className="flex flex-col gap-3">
          {values.map((v) => {
            const meta = lookupIndicator(v.indicator_code);
            return (
              <div
                key={v.indicator_code}
                className="flex flex-col gap-1 rounded-md border bg-card p-3"
              >
                <div className="flex items-center justify-between">
                  <p className="text-sm font-medium">{meta.name}</p>
                  {renderValue(v)}
                </div>
                <p className="text-xs text-muted-foreground">
                  {meta.interpretation}
                </p>
              </div>
            );
          })}
        </CardContent>
      )}
    </Card>
  );
}

function renderValue(v: RiskIndicatorValueOut) {
  if (v.value_boolean === true) {
    return <Badge variant="danger">Спрацював</Badge>;
  }
  if (v.value_boolean === false) {
    return <Badge variant="success">Не спрацював</Badge>;
  }
  if (v.value_numeric !== null) {
    const num = Number(v.value_numeric);
    const formatted = Number.isFinite(num) ? num.toFixed(3) : v.value_numeric;
    return <Badge variant="default">{formatted}</Badge>;
  }
  return <Badge variant="secondary">Невідомо</Badge>;
}
