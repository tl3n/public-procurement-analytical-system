import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export interface TimeRange {
  since?: string;
  until?: string;
}

interface Props {
  value: TimeRange;
  onChange: (range: TimeRange) => void;
}

export function TimeRangeControls({ value, onChange }: Props) {
  const [local, setLocal] = useState<TimeRange>(value);

  function apply() {
    onChange(local);
  }
  function reset() {
    setLocal({});
    onChange({});
  }

  return (
    <Card className="flex flex-wrap items-end gap-4 p-4">
      <div className="flex flex-col gap-1">
        <Label>Дата від</Label>
        <Input
          type="date"
          value={local.since?.slice(0, 10) ?? ""}
          onChange={(e) =>
            setLocal((s) => ({
              ...s,
              since: e.target.value ? `${e.target.value}T00:00:00Z` : undefined,
            }))
          }
        />
      </div>
      <div className="flex flex-col gap-1">
        <Label>Дата до</Label>
        <Input
          type="date"
          value={local.until?.slice(0, 10) ?? ""}
          onChange={(e) =>
            setLocal((s) => ({
              ...s,
              until: e.target.value ? `${e.target.value}T00:00:00Z` : undefined,
            }))
          }
        />
      </div>
      <div className="flex gap-2">
        <Button size="sm" onClick={apply}>
          Застосувати
        </Button>
        <Button size="sm" variant="outline" onClick={reset}>
          Скинути
        </Button>
      </div>
    </Card>
  );
}
