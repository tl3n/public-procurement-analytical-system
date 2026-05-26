import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";

export interface TimeRange {
  since?: string;
  until?: string;
}

interface Props {
  value: TimeRange;
  onChange: (range: TimeRange) => void;
}

type PresetKey = "30d" | "90d" | "365d" | "ytd" | "all";

const PRESETS: Array<{ key: PresetKey; label: string }> = [
  { key: "30d", label: "30 днів" },
  { key: "90d", label: "90 днів" },
  { key: "365d", label: "12 місяців" },
  { key: "ytd", label: "Цей рік" },
  { key: "all", label: "За весь час" },
];

function isoStartOfDay(d: Date): string {
  const copy = new Date(d);
  copy.setUTCHours(0, 0, 0, 0);
  return copy.toISOString();
}

function rangeForPreset(key: PresetKey): TimeRange {
  if (key === "all") return {};
  const now = new Date();
  if (key === "ytd") {
    const jan1 = new Date(Date.UTC(now.getUTCFullYear(), 0, 1));
    return { since: isoStartOfDay(jan1) };
  }
  const days = key === "30d" ? 30 : key === "90d" ? 90 : 365;
  const since = new Date(now);
  since.setUTCDate(since.getUTCDate() - days);
  return { since: isoStartOfDay(since) };
}

function presetMatches(preset: PresetKey, value: TimeRange): boolean {
  const target = rangeForPreset(preset);
  return (
    (target.since ?? null) === (value.since ?? null) &&
    (target.until ?? null) === (value.until ?? null)
  );
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
  function applyPreset(key: PresetKey) {
    const next = rangeForPreset(key);
    setLocal(next);
    onChange(next);
  }

  return (
    <Card className="flex flex-col gap-4 p-4">
      <div className="flex flex-wrap items-center gap-1.5">
        <span className="mr-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">
          Швидкий вибір
        </span>
        {PRESETS.map(({ key, label }) => {
          const active = presetMatches(key, value);
          return (
            <Button
              key={key}
              size="sm"
              variant={active ? "default" : "outline"}
              className={cn(
                "h-7 px-2.5 text-xs",
                !active && "border-border/60 text-muted-foreground",
              )}
              onClick={() => applyPreset(key)}
            >
              {label}
            </Button>
          );
        })}
      </div>
      <div className="flex flex-wrap items-end gap-3 border-t border-border/60 pt-4">
        <div className="flex flex-col gap-1">
          <Label className="text-xs uppercase tracking-wider text-muted-foreground">
            Дата від
          </Label>
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
          <Label className="text-xs uppercase tracking-wider text-muted-foreground">
            Дата до
          </Label>
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
      </div>
    </Card>
  );
}
