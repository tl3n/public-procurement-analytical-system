import type { CorrelationResponse } from "@/api/types";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { formatCount } from "@/lib/format";

interface Props {
  data: CorrelationResponse;
}

export function CorrelationBlock({ data }: Props) {
  const hasData = data.n_pairs >= 2;

  return (
    <Card className="p-4">
      <CardHeader className="p-0 pb-3">
        <CardTitle className="text-base">
          Кореляція конкуренції та цінового відхилення
        </CardTitle>
        <CardDescription>
          Зв'язок між кількістю учасників тендеру та відхиленням ціни від
          медіани CPV
        </CardDescription>
      </CardHeader>
      <CardContent className="p-0">
        {!hasData ? (
          <p className="text-sm text-muted-foreground">
            Недостатньо даних. Запустіть обчислення індикаторів через{" "}
            <code className="rounded bg-muted px-1 py-0.5 text-xs">
              POST /admin/recompute
            </code>
            .
          </p>
        ) : (
          <div className="flex flex-col gap-3">
            <div className="grid grid-cols-2 gap-4">
              <StatCell
                label="Пірсон (r)"
                value={data.pearson != null ? data.pearson.toFixed(3) : "—"}
              />
              <StatCell
                label="Спірмен (ρ)"
                value={data.spearman != null ? data.spearman.toFixed(3) : "—"}
              />
            </div>
            <p className="text-xs text-muted-foreground">
              <span className="font-medium text-foreground">
                {data.strength} кореляція.
              </span>{" "}
              Базується на {formatCount(data.n_pairs)} парах спостережень
              (тендер → кількість пропозицій + цінове відхилення).
            </p>
            {data.pearson != null && data.pearson < -0.05 && (
              <p className="rounded-md border border-green-200 bg-green-50 px-3 py-2 text-xs text-green-800">
                Від'ємне значення підтверджує теоретичне припущення: більше
                учасників → нижче цінове відхилення від ринкової медіани.
              </p>
            )}
            {data.pearson != null && data.pearson > 0.05 && (
              <p className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">
                Додатнє значення є нетиповим: вища конкуренція корелює з вищим
                ціновим відхиленням. Варто перевірити якість даних або звузити
                вибірку.
              </p>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function StatCell({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border bg-muted/40 p-3">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-1 text-2xl font-bold tracking-tight">{value}</p>
    </div>
  );
}
