import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";

export interface Filters {
  cpv?: string;
  region?: string;
  procurement_method_type?: string;
  date_from?: string;
  date_to?: string;
  value_min?: string;
  value_max?: string;
}

const PROCEDURE_TYPES = [
  "open",
  "aboveThreshold",
  "aboveThresholdUA",
  "aboveThresholdEU",
  "belowThreshold",
  "priceQuotation",
  "negotiation",
  "negotiation.quick",
  "reporting",
  "competitiveOrdering",
  "competitiveDialogueUA",
  "competitiveDialogueEU",
];

interface Props {
  values: Filters;
  onApply: (filters: Filters) => void;
  onReset: () => void;
}

export function FilterSidebar({ values, onApply, onReset }: Props) {
  function update<K extends keyof Filters>(key: K, v: Filters[K]) {
    onApply({ ...values, [key]: v || undefined });
  }

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-sm">Фільтри</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <Field label="CPV код">
          <Input
            value={values.cpv ?? ""}
            placeholder="напр. 15810000-9"
            onChange={(e) => update("cpv", e.target.value)}
          />
        </Field>
        <Field label="Регіон замовника">
          <Input
            value={values.region ?? ""}
            placeholder="напр. Київ"
            onChange={(e) => update("region", e.target.value)}
          />
        </Field>
        <Field label="Тип процедури">
          <Select
            value={values.procurement_method_type ?? ""}
            onChange={(e) =>
              update("procurement_method_type", e.target.value)
            }
          >
            <option value="">— будь-який —</option>
            {PROCEDURE_TYPES.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </Select>
        </Field>
        <div className="grid grid-cols-2 gap-2">
          <Field label="Дата від">
            <Input
              type="date"
              value={values.date_from?.slice(0, 10) ?? ""}
              onChange={(e) =>
                update(
                  "date_from",
                  e.target.value ? `${e.target.value}T00:00:00Z` : undefined,
                )
              }
            />
          </Field>
          <Field label="Дата до">
            <Input
              type="date"
              value={values.date_to?.slice(0, 10) ?? ""}
              onChange={(e) =>
                update(
                  "date_to",
                  e.target.value ? `${e.target.value}T00:00:00Z` : undefined,
                )
              }
            />
          </Field>
        </div>
        <div className="grid grid-cols-2 gap-2">
          <Field label="Вартість від, грн">
            <Input
              type="number"
              inputMode="numeric"
              value={values.value_min ?? ""}
              onChange={(e) => update("value_min", e.target.value)}
            />
          </Field>
          <Field label="Вартість до, грн">
            <Input
              type="number"
              inputMode="numeric"
              value={values.value_max ?? ""}
              onChange={(e) => update("value_max", e.target.value)}
            />
          </Field>
        </div>
        <Button variant="outline" size="sm" onClick={onReset}>
          Скинути фільтри
        </Button>
      </CardContent>
    </Card>
  );
}

function Field({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-1">
      <Label>{label}</Label>
      {children}
    </div>
  );
}
