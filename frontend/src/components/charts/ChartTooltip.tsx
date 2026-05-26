import type { TooltipProps } from "recharts";

interface Props extends TooltipProps<number, string> {
  formatValue?: (value: number, name: string) => string;
  formatLabel?: (label: string) => string;
}

/** Branded Recharts tooltip — uses our card surface and tabular numerals so
 *  it stops looking like the default white-box Recharts default. */
export function ChartTooltip({
  active,
  payload,
  label,
  formatValue,
  formatLabel,
}: Props) {
  if (!active || !payload || payload.length === 0) return null;

  return (
    <div className="rounded-lg border border-border/70 bg-card/95 px-3 py-2 text-xs shadow-lg shadow-foreground/[0.08] backdrop-blur-sm">
      {label != null && (
        <p className="mb-1 font-semibold text-foreground">
          {formatLabel ? formatLabel(String(label)) : String(label)}
        </p>
      )}
      <ul className="flex flex-col gap-0.5">
        {payload.map((entry, idx) => {
          const value = Number(entry.value);
          const name = String(entry.name ?? entry.dataKey ?? "");
          return (
            <li key={idx} className="flex items-center gap-2">
              <span
                className="h-2 w-2 shrink-0 rounded-full"
                style={{ background: entry.color ?? entry.stroke ?? "currentColor" }}
              />
              <span className="text-muted-foreground">{name}</span>
              <span className="ml-auto font-mono font-medium text-foreground">
                {formatValue
                  ? formatValue(value, name)
                  : Number.isFinite(value)
                    ? value.toLocaleString("uk-UA")
                    : String(entry.value)}
              </span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
